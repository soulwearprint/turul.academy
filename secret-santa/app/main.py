"""Family Secret Santa — FastAPI app.

Run:  uvicorn app.main:app --port 8080   (from the secret-santa/ folder)
"""
from __future__ import annotations

import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import crypto, db, draw, google_auth, mailer

MAX_ADMINS = 5
SESSION_TTL = 30 * 60  # seconds, sliding
COOKIE = "santa_session"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATIC = Path(__file__).resolve().parent / "static"



@asynccontextmanager
async def lifespan(_app):
    db.init()
    yield


app = FastAPI(title="Family Secret Santa", docs_url=None, redoc_url=None, lifespan=lifespan)


# ─── Sessions ──────────────────────────────────────────────────────────────
# The unwrapped master key lives only in server memory for the session's
# lifetime. A restart logs everybody out, which is intended.

@dataclass
class Session:
    admin_id: int
    admin_name: str
    key: bytes
    expires: float
    reauth_until: float = 0.0  # set by a fresh Google sign-in; allows one unlock


_sessions: dict[str, Session] = {}
_oauth_pending: dict[str, dict] = {}  # state -> {nonce, purpose, year, session, expires}
OAUTH_COOKIE = "santa_oauth"
SERVER_COPY = "server_wrapped_key"


def _new_session(admin_id: int, name: str, key: bytes) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = Session(admin_id, name, key, time.time() + SESSION_TTL)
    return token


def _ensure_server_copy(conn, key: bytes) -> None:
    """With Google sign-in enabled, keep a copy of the master key wrapped with
    SANTA_SERVER_KEY so Google-only admins can work with the matches."""
    if google_auth.enabled() and not db.get_setting(conn, SERVER_COPY):
        db.set_setting(conn, SERVER_COPY, crypto.wrap_with_kek(key, google_auth.server_kek()))


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=SESSION_TTL,
                    secure=os.environ.get("SANTA_SECURE_COOKIE", "0") == "1")


def current(request: Request) -> Session:
    token = request.cookies.get(COOKIE, "")
    s = _sessions.get(token)
    if not s or s.expires < time.time():
        _sessions.pop(token, None)
        raise HTTPException(401, "Please log in as an admin.")
    s.expires = time.time() + SESSION_TTL
    return s


def _check_password(conn, admin_id: int, password: str) -> bytes:
    row = conn.execute("SELECT key_salt, wrapped_key FROM admins WHERE id = ?", (admin_id,)).fetchone()
    if not row:
        raise HTTPException(401, "Unknown admin.")
    if not row["key_salt"]:
        raise HTTPException(403, "This admin has no password and signs in with Google.")
    try:
        return crypto.unwrap_key(row["key_salt"], row["wrapped_key"], password)
    except crypto.WrongPassword:
        raise HTTPException(403, "Wrong password.")


# ─── Models ────────────────────────────────────────────────────────────────

class SetupIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=6, max_length=200)
    google_email: str = Field(default="", max_length=200)


class AdminIn(BaseModel):
    """A new admin signs in with a password, with Google, or with both."""
    name: str = Field(min_length=1, max_length=60)
    password: str = Field(default="", max_length=200)
    google_email: str = Field(default="", max_length=200)


class AdminGoogleIn(BaseModel):
    google_email: str = Field(default="", max_length=200)


class LoginIn(BaseModel):
    name: str
    password: str


class PasswordChangeIn(BaseModel):
    current: str = ""  # empty when setting a first password for a Google-only admin
    new: str = Field(min_length=6, max_length=200)


class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=200)
    lang: Literal["hu", "en"] = "hu"  # postcard language


class ExclusionIn(BaseModel):
    a_id: int
    b_id: int


class YearIn(BaseModel):
    year: int = Field(ge=2000, le=2200)


class YearDetailsIn(BaseModel):
    budget: str = Field(default="", max_length=80)
    exchange_date: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=600)
    avoid_repeat: bool = True  # nobody draws the same person as last year


class ParticipantsIn(BaseModel):
    member_ids: list[int]


class ReshuffleIn(BaseModel):
    selected_ids: list[int] = []
    everyone: bool = False
    confirm: bool = False


class NotifyIn(BaseModel):
    member_ids: list[int] | None = None  # None = everyone still pending


class RevealIn(BaseModel):
    password: str = ""  # or empty right after a fresh Google sign-in


# ─── Setup / auth ──────────────────────────────────────────────────────────

@app.get("/api/status")
def status(request: Request):
    with db.connect() as conn:
        n_admins = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
        s = _sessions.get(request.cookies.get(COOKIE, ""))
        logged = bool(s and s.expires > time.time())
        me = conn.execute("SELECT key_salt, google_email FROM admins WHERE id = ?", (s.admin_id,)).fetchone() if logged else None
    return {
        "setup_done": n_admins > 0,
        "logged_in": logged,
        "admin": {"id": s.admin_id, "name": s.admin_name, "has_password": bool(me and me["key_salt"]),
                  "google_email": (me and me["google_email"]) or ""} if logged and me else None,
        "mail_mode": mailer.mode(),
        "google_enabled": google_auth.enabled(),
        "google_setup": google_auth.enabled() and bool(os.environ.get("SANTA_FIRST_ADMIN_EMAIL", "").strip()),
    }


@app.post("/api/setup")
def setup(body: SetupIn, response: Response):
    """Create the first (mandatory) admin and the master key. Only works once."""
    first = os.environ.get("SANTA_FIRST_ADMIN_EMAIL", "").strip().lower()
    if first:
        raise HTTPException(403, "Setup is reserved for the configured first admin: use Sign in with Google.")
    gmail = _clean_google(body.google_email)
    with db.connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]:
            raise HTTPException(409, "Setup already done.")
        key = crypto.new_master_key()
        salt, wrapped = crypto.wrap_key(key, body.password)
        cur = conn.execute(
            "INSERT INTO admins (slot, name, key_salt, wrapped_key, google_email, created_at) VALUES (1, ?, ?, ?, ?, ?)",
            (body.name.strip(), salt, wrapped, gmail, db.now()),
        )
        _ensure_server_copy(conn, key)
        db.audit(conn, body.name.strip(), "setup", "first admin created")
        token = _new_session(cur.lastrowid, body.name.strip(), key)
    _set_cookie(response, token)
    return {"ok": True}


@app.post("/api/login")
def login(body: LoginIn, response: Response):
    with db.connect() as conn:
        row = conn.execute("SELECT id, name FROM admins WHERE name = ?", (body.name.strip(),)).fetchone()
        if not row:
            raise HTTPException(403, "Wrong name or password.")
        try:
            key = _check_password(conn, row["id"], body.password)
        except HTTPException:
            raise HTTPException(403, "Wrong name or password.")
        _ensure_server_copy(conn, key)
        db.audit(conn, row["name"], "login")
    _set_cookie(response, _new_session(row["id"], row["name"], key))
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    _sessions.pop(request.cookies.get(COOKIE, ""), None)
    response.delete_cookie(COOKIE)
    return {"ok": True}


# ─── Google sign-in ────────────────────────────────────────────────────────

def _clean_google(email: str) -> str | None:
    email = (email or "").strip().lower()
    if not email:
        return None
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "That does not look like a Google account e-mail.")
    return email


def _server_key(conn) -> bytes:
    wrapped = db.get_setting(conn, SERVER_COPY)
    if not wrapped:
        raise HTTPException(409, "Google sign-in is not ready yet: a password admin must log in once first.")
    return crypto.unwrap_with_kek(wrapped, google_auth.server_kek())


@app.get("/auth/google/start", include_in_schema=False)
def google_start(request: Request, purpose: Literal["login", "reveal"] = "login", year: int = 0):
    if not google_auth.enabled():
        raise HTTPException(404, "Google sign-in is not configured.")
    session_token = ""
    hint = ""
    if purpose == "reveal":
        s = current(request)  # same-site request, so the session cookie is present
        session_token = request.cookies.get(COOKIE, "")
        with db.connect() as conn:
            row = conn.execute("SELECT google_email FROM admins WHERE id = ?", (s.admin_id,)).fetchone()
        hint = (row and row["google_email"]) or ""
        if not hint:
            raise HTTPException(400, "Your admin account has no Google e-mail.")
    for k, v in list(_oauth_pending.items()):
        if v["expires"] < time.time():
            _oauth_pending.pop(k, None)
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    _oauth_pending[state] = {"nonce": nonce, "purpose": purpose, "year": year,
                             "session": session_token, "expires": time.time() + 600}
    resp = RedirectResponse(google_auth.authorization_url(state, nonce, reauth=purpose == "reveal", login_hint=hint))
    # Lax (not Strict) so the cookie survives the top-level redirect back from Google.
    resp.set_cookie(OAUTH_COOKIE, state, httponly=True, samesite="lax", max_age=600,
                    secure=os.environ.get("SANTA_SECURE_COOKIE", "0") == "1")
    return resp


def _google_fail(msg: str) -> RedirectResponse:
    from urllib.parse import quote
    resp = RedirectResponse(f"/#error={quote(msg)}", status_code=303)
    resp.delete_cookie(OAUTH_COOKIE)
    return resp


@app.get("/auth/google/callback", include_in_schema=False)
def google_callback(request: Request, state: str = "", code: str = "", error: str = ""):
    pending = _oauth_pending.pop(state, None)
    if error:
        return _google_fail("Google sign-in was cancelled.")
    if not pending or pending["expires"] < time.time() or request.cookies.get(OAUTH_COOKIE) != state:
        return _google_fail("Sign-in link expired. Please try again.")
    try:
        claims = google_auth.verify_claims(google_auth.exchange_code(code), pending["nonce"],
                                           require_fresh=pending["purpose"] == "reveal")
    except (google_auth.GoogleAuthError, KeyError) as exc:
        return _google_fail(str(exc))
    email = claims["email"].strip().lower()

    with db.connect() as conn:
        admin = conn.execute("SELECT id, name FROM admins WHERE google_email = ?", (email,)).fetchone()

        if pending["purpose"] == "reveal":
            s = _sessions.get(pending["session"])
            if not s or not admin or admin["id"] != s.admin_id:
                return _google_fail("Please confirm with the Google account of the admin who is logged in.")
            s.reauth_until = time.time() + google_auth.REAUTH_MAX_AGE
            resp = RedirectResponse(f"/#reveal={int(pending['year'])}", status_code=303)
            resp.delete_cookie(OAUTH_COOKIE)
            return resp

        n_admins = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
        if not admin and n_admins == 0:
            first = os.environ.get("SANTA_FIRST_ADMIN_EMAIL", "").strip().lower()
            if first != email:  # unset = Google setup disabled, so nobody can grab slot 1
                return _google_fail("Only the configured first admin can set up this app.")
            key = crypto.new_master_key()
            name = (claims.get("given_name") or claims.get("name") or email.split("@")[0])[:60]
            cur = conn.execute(
                "INSERT INTO admins (slot, name, key_salt, wrapped_key, google_email, created_at) VALUES (1, ?, '', '', ?, ?)",
                (name, email, db.now()),
            )
            _ensure_server_copy(conn, key)
            db.audit(conn, name, "setup", f"first admin created via Google ({email})")
            admin = {"id": cur.lastrowid, "name": name}
        elif not admin:
            db.audit(conn, email, "REJECTED Google sign-in", "not an admin")
            return _google_fail(f"{email} is not an admin of this Secret Santa.")
        else:
            key = _server_key(conn)
            db.audit(conn, admin["name"], "login", "Google")
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie(OAUTH_COOKIE)
    _set_cookie(resp, _new_session(admin["id"], admin["name"], key))
    return resp


# ─── Admins (max 5; slot 1 is mandatory and permanent) ─────────────────────

@app.get("/api/admins")
def list_admins(s: Session = Depends(current)):
    with db.connect() as conn:
        rows = conn.execute("SELECT id, slot, name, google_email, key_salt != '' AS has_password, created_at "
                            "FROM admins ORDER BY slot").fetchall()
    return [{**dict(r), "google_email": r["google_email"] or "", "has_password": bool(r["has_password"])} for r in rows]


@app.post("/api/admins")
def add_admin(body: AdminIn, s: Session = Depends(current)):
    with db.connect() as conn:
        used = {r[0] for r in conn.execute("SELECT slot FROM admins")}
        free = [n for n in range(1, MAX_ADMINS + 1) if n not in used]
        if not free:
            raise HTTPException(409, f"Maximum of {MAX_ADMINS} admins reached.")
        if conn.execute("SELECT 1 FROM admins WHERE name = ?", (body.name.strip(),)).fetchone():
            raise HTTPException(409, "An admin with this name already exists.")
        gmail = _clean_google(body.google_email)
        if not body.password and not gmail:
            raise HTTPException(422, "Give the new admin a password, a Google e-mail, or both.")
        if body.password and len(body.password) < 6:
            raise HTTPException(422, "Passwords need at least 6 characters.")
        if gmail and conn.execute("SELECT 1 FROM admins WHERE google_email = ?", (gmail,)).fetchone():
            raise HTTPException(409, "That Google account is already an admin.")
        salt, wrapped = crypto.wrap_key(s.key, body.password) if body.password else ("", "")
        conn.execute(
            "INSERT INTO admins (slot, name, key_salt, wrapped_key, google_email, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (free[0], body.name.strip(), salt, wrapped, gmail, db.now()),
        )
        if gmail:
            _ensure_server_copy(conn, s.key)
        db.audit(conn, s.admin_name, "admin added", body.name.strip())
    return {"ok": True}


@app.delete("/api/admins/{admin_id}")
def remove_admin(admin_id: int, s: Session = Depends(current)):
    with db.connect() as conn:
        row = conn.execute("SELECT slot, name FROM admins WHERE id = ?", (admin_id,)).fetchone()
        if not row:
            raise HTTPException(404, "No such admin.")
        if row["slot"] == 1:
            raise HTTPException(400, "The first admin is mandatory and cannot be removed.")
        conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
        db.audit(conn, s.admin_name, "admin removed", row["name"])
    for tok, sess in list(_sessions.items()):
        if sess.admin_id == admin_id:
            _sessions.pop(tok, None)
    return {"ok": True}


@app.put("/api/admins/{admin_id}/google")
def set_admin_google(admin_id: int, body: AdminGoogleIn, s: Session = Depends(current)):
    gmail = _clean_google(body.google_email)
    with db.connect() as conn:
        row = conn.execute("SELECT name, key_salt FROM admins WHERE id = ?", (admin_id,)).fetchone()
        if not row:
            raise HTTPException(404, "No such admin.")
        if not gmail and not row["key_salt"]:
            raise HTTPException(400, "This admin has no password, so the Google e-mail can't be removed.")
        if gmail and conn.execute("SELECT 1 FROM admins WHERE google_email = ? AND id != ?", (gmail, admin_id)).fetchone():
            raise HTTPException(409, "That Google account is already an admin.")
        conn.execute("UPDATE admins SET google_email = ? WHERE id = ?", (gmail, admin_id))
        if gmail:
            _ensure_server_copy(conn, s.key)
        db.audit(conn, s.admin_name, "admin Google e-mail changed", f"{row['name']}: {gmail or '(removed)'}")
    return {"ok": True}


@app.post("/api/admins/me/password")
def change_password(body: PasswordChangeIn, s: Session = Depends(current)):
    with db.connect() as conn:
        has_pw = conn.execute("SELECT key_salt FROM admins WHERE id = ?", (s.admin_id,)).fetchone()["key_salt"]
        key = _check_password(conn, s.admin_id, body.current) if has_pw else s.key
        salt, wrapped = crypto.wrap_key(key, body.new)
        conn.execute("UPDATE admins SET key_salt = ?, wrapped_key = ? WHERE id = ?", (salt, wrapped, s.admin_id))
        db.audit(conn, s.admin_name, "password changed")
    return {"ok": True}


# ─── Family members ────────────────────────────────────────────────────────

def _clean_member(body: MemberIn) -> tuple[str, str, str]:
    email = body.email.strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "That does not look like an e-mail address.")
    return body.name.strip(), email, body.lang


@app.get("/api/members")
def list_members(s: Session = Depends(current)):
    with db.connect() as conn:
        rows = conn.execute("SELECT id, name, email, lang, archived FROM members ORDER BY archived, name COLLATE NOCASE").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/members")
def add_member(body: MemberIn, s: Session = Depends(current)):
    name, email, lang = _clean_member(body)
    with db.connect() as conn:
        cur = conn.execute("INSERT INTO members (name, email, lang, created_at) VALUES (?, ?, ?, ?)",
                           (name, email, lang, db.now()))
        db.audit(conn, s.admin_name, "member added", name)
    return {"id": cur.lastrowid}


@app.put("/api/members/{member_id}")
def edit_member(member_id: int, body: MemberIn, s: Session = Depends(current)):
    name, email, lang = _clean_member(body)
    with db.connect() as conn:
        if not conn.execute("UPDATE members SET name = ?, email = ?, lang = ?, archived = 0 WHERE id = ?",
                            (name, email, lang, member_id)).rowcount:
            raise HTTPException(404, "No such member.")
        db.audit(conn, s.admin_name, "member edited", name)
    return {"ok": True}


@app.delete("/api/members/{member_id}")
def delete_member(member_id: int, s: Session = Depends(current)):
    """Members used in any year are archived (history stays intact), others deleted."""
    with db.connect() as conn:
        row = conn.execute("SELECT name FROM members WHERE id = ?", (member_id,)).fetchone()
        if not row:
            raise HTTPException(404, "No such member.")
        used = conn.execute(
            "SELECT 1 FROM year_participants WHERE member_id = ? UNION SELECT 1 FROM pairings WHERE giver_id = ?",
            (member_id, member_id),
        ).fetchone()
        if used:
            conn.execute("UPDATE members SET archived = 1 WHERE id = ?", (member_id,))
        else:
            conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        db.audit(conn, s.admin_name, "member archived" if used else "member deleted", row["name"])
    return {"archived": bool(used)}


# ─── Exclusions (e.g. couples never draw each other) ───────────────────────

@app.get("/api/exclusions")
def list_exclusions(s: Session = Depends(current)):
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT e.a_id, e.b_id, a.name AS a_name, b.name AS b_name FROM exclusions e "
            "JOIN members a ON a.id = e.a_id JOIN members b ON b.id = e.b_id ORDER BY a.name COLLATE NOCASE"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/exclusions")
def add_exclusion(body: ExclusionIn, s: Session = Depends(current)):
    a, b = sorted((body.a_id, body.b_id))
    if a == b:
        raise HTTPException(422, "Pick two different people.")
    with db.connect() as conn:
        names = _names(conn, [a, b])
        if len(names) != 2:
            raise HTTPException(404, "Unknown member.")
        conn.execute("INSERT OR IGNORE INTO exclusions (a_id, b_id) VALUES (?, ?)", (a, b))
        db.audit(conn, s.admin_name, "exclusion added", f"{names[a]} ↔ {names[b]}")
    return {"ok": True}


@app.delete("/api/exclusions/{a_id}/{b_id}")
def delete_exclusion(a_id: int, b_id: int, s: Session = Depends(current)):
    a, b = sorted((a_id, b_id))
    with db.connect() as conn:
        names = _names(conn, [a, b])
        conn.execute("DELETE FROM exclusions WHERE a_id = ? AND b_id = ?", (a, b))
        db.audit(conn, s.admin_name, "exclusion removed", f"{names.get(a, '?')} ↔ {names.get(b, '?')}")
    return {"ok": True}


def _forbidden(conn, key: bytes, year: int) -> draw.Forbidden:
    """Who may not draw whom in ``year``: exclusions both ways, plus (if the
    year says so) each person's match from the most recent earlier draw."""
    out: draw.Forbidden = {}
    for r in conn.execute("SELECT a_id, b_id FROM exclusions"):
        out.setdefault(r["a_id"], set()).add(r["b_id"])
        out.setdefault(r["b_id"], set()).add(r["a_id"])
    y = conn.execute("SELECT avoid_repeat FROM years WHERE year = ?", (year,)).fetchone()
    if y and y["avoid_repeat"]:
        prev = conn.execute("SELECT MAX(year) FROM pairings WHERE year < ?", (year,)).fetchone()[0]
        if prev is not None:
            for g, r in _load_pairing(conn, key, prev).items():
                out.setdefault(g, set()).add(r)
    return out


# ─── Years ─────────────────────────────────────────────────────────────────

def _year_or_404(conn, year: int):
    row = conn.execute("SELECT * FROM years WHERE year = ?", (year,)).fetchone()
    if not row:
        raise HTTPException(404, f"No Secret Santa set up for {year}.")
    return row


def _state(conn, year: int) -> dict:
    participants = {r[0] for r in conn.execute("SELECT member_id FROM year_participants WHERE year = ?", (year,))}
    givers = {r[0] for r in conn.execute("SELECT giver_id FROM pairings WHERE year = ?", (year,))}
    return {
        "participants": participants,
        "givers": givers,
        "drawn": bool(givers),
        "added": participants - givers if givers else set(),
        "removed": givers - participants,
        "in_sync": bool(givers) and participants == givers,
    }


def _names(conn, ids) -> dict[int, str]:
    ids = list(ids)
    if not ids:
        return {}
    q = ",".join("?" * len(ids))
    return {r["id"]: r["name"] for r in conn.execute(f"SELECT id, name FROM members WHERE id IN ({q})", ids)}


@app.get("/api/years")
def list_years(s: Session = Depends(current)):
    out = []
    with db.connect() as conn:
        for r in conn.execute("SELECT year FROM years ORDER BY year DESC").fetchall():
            st = _state(conn, r["year"])
            out.append({"year": r["year"], "participants": len(st["participants"]),
                        "drawn": st["drawn"], "in_sync": st["in_sync"]})
    return out


@app.post("/api/years")
def create_year(body: YearIn, s: Session = Depends(current)):
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM years WHERE year = ?", (body.year,)).fetchone():
            raise HTTPException(409, f"{body.year} already exists.")
        prev = conn.execute("SELECT * FROM years WHERE year < ? ORDER BY year DESC LIMIT 1", (body.year,)).fetchone()
        conn.execute(
            "INSERT INTO years (year, budget, exchange_date, note, avoid_repeat, created_at) VALUES (?, ?, '', ?, ?, ?)",
            (body.year, prev["budget"] if prev else "", prev["note"] if prev else "",
             prev["avoid_repeat"] if prev else 1, db.now()),
        )
        if prev:  # start from last year's list, minus archived members
            conn.execute(
                "INSERT INTO year_participants (year, member_id) SELECT ?, yp.member_id FROM year_participants yp "
                "JOIN members m ON m.id = yp.member_id WHERE yp.year = ? AND m.archived = 0",
                (body.year, prev["year"]),
            )
        else:
            conn.execute("INSERT INTO year_participants (year, member_id) SELECT ?, id FROM members WHERE archived = 0", (body.year,))
        db.audit(conn, s.admin_name, "year created", str(body.year))
    return {"ok": True}


@app.get("/api/years/{year}")
def get_year(year: int, s: Session = Depends(current)):
    with db.connect() as conn:
        y = _year_or_404(conn, year)
        st = _state(conn, year)
        names = _names(conn, st["participants"] | st["givers"])
        notif = {r["giver_id"]: (r["notified_at"], r["notify_count"]) for r in
                 conn.execute("SELECT giver_id, notified_at, notify_count FROM pairings WHERE year = ?", (year,))}
    people = [
        {"id": mid, "name": names.get(mid, "?"),
         "notified_at": notif.get(mid, (None, 0))[0],
         "has_match": mid in st["givers"]}
        for mid in sorted(st["participants"], key=lambda i: names.get(i, "").lower())
    ]
    return {
        "year": year,
        "budget": y["budget"], "exchange_date": y["exchange_date"], "note": y["note"],
        "avoid_repeat": bool(y["avoid_repeat"]),
        "participants": people,
        "drawn": st["drawn"],
        "in_sync": st["in_sync"],
        "added": [{"id": i, "name": names.get(i, "?")} for i in sorted(st["added"])],
        "removed": [{"id": i, "name": names.get(i, "?")} for i in sorted(st["removed"])],
    }


@app.put("/api/years/{year}")
def edit_year(year: int, body: YearDetailsIn, s: Session = Depends(current)):
    with db.connect() as conn:
        _year_or_404(conn, year)
        conn.execute("UPDATE years SET budget = ?, exchange_date = ?, note = ?, avoid_repeat = ? WHERE year = ?",
                     (body.budget.strip(), body.exchange_date.strip(), body.note.strip(), int(body.avoid_repeat), year))
        db.audit(conn, s.admin_name, "year details edited", str(year))
    return {"ok": True}


@app.delete("/api/years/{year}")
def delete_year(year: int, s: Session = Depends(current)):
    with db.connect() as conn:
        _year_or_404(conn, year)
        conn.execute("DELETE FROM years WHERE year = ?", (year,))
        db.audit(conn, s.admin_name, "year deleted", str(year))
    return {"ok": True}


@app.put("/api/years/{year}/participants")
def set_participants(year: int, body: ParticipantsIn, s: Session = Depends(current)):
    """Change who takes part. Existing matches are NOT touched here; if a draw
    exists the response says so and the UI asks which names to reshuffle."""
    ids = set(body.member_ids)
    with db.connect() as conn:
        _year_or_404(conn, year)
        known = {r[0] for r in conn.execute("SELECT id FROM members")}
        if ids - known:
            raise HTTPException(422, "Unknown member id(s).")
        conn.execute("DELETE FROM year_participants WHERE year = ?", (year,))
        conn.executemany("INSERT INTO year_participants (year, member_id) VALUES (?, ?)", [(year, i) for i in ids])
        db.audit(conn, s.admin_name, "participants changed", f"{year}: {len(ids)} people")
        st = _state(conn, year)
    return {"drawn": st["drawn"], "in_sync": st["in_sync"], "needs_reshuffle": st["drawn"] and not st["in_sync"]}


def _load_pairing(conn, key: bytes, year: int) -> dict[int, int]:
    rows = conn.execute("SELECT giver_id, receiver_sealed FROM pairings WHERE year = ?", (year,)).fetchall()
    return {r["giver_id"]: crypto.open_receiver(key, year, r["giver_id"], r["receiver_sealed"]) for r in rows}


def _plan(conn, s: Session, year: int, body: ReshuffleIn) -> tuple[draw.ReshufflePlan, set[int]]:
    st = _state(conn, year)
    people = st["participants"]
    if len(people) < 2:
        raise HTTPException(422, "At least 2 participants are needed.")
    rules = _forbidden(conn, s.key, year)
    if not st["drawn"]:
        pairing = draw.full_draw(people, forbidden=rules)
        return draw.ReshufflePlan(pairing, set(people), set(people), set()), people
    old = _load_pairing(conn, s.key, year)
    selected = people if body.everyone else set(body.selected_ids) & people
    return draw.partial_reshuffle(old, people, selected, forbidden=rules), people


@app.post("/api/years/{year}/draw")
def run_draw(year: int, body: ReshuffleIn, s: Session = Depends(current)):
    """First draw, or a (partial) reshuffle of an existing one.

    For an existing draw, ``confirm`` must be true: the UI first shows which
    names will be reshuffled (selected + new members + a hidden count)."""
    with db.connect() as conn:
        _year_or_404(conn, year)
        st = _state(conn, year)
        if st["drawn"] and not body.confirm:
            raise HTTPException(409, "A draw already exists. Confirm which names to reshuffle.")
        try:
            plan, people = _plan(conn, s, year, body)
        except draw.DrawError as exc:
            raise HTTPException(422, str(exc))
        prev = {r["giver_id"]: r["notify_count"] for r in
                conn.execute("SELECT giver_id, notify_count FROM pairings WHERE year = ?", (year,))}
        conn.execute(
            f"DELETE FROM pairings WHERE year = ? AND giver_id NOT IN ({','.join('?' * len(people))})",
            (year, *people),
        )
        for giver in plan.reshuffled:
            sealed = crypto.seal_receiver(s.key, year, giver, plan.pairing[giver])
            # Everyone redrawn is re-notified, even if they drew the same person
            # again, so the notification list does not reveal who really changed.
            conn.execute(
                "INSERT INTO pairings (year, giver_id, receiver_sealed, assigned_at, notified_at, notify_count) "
                "VALUES (?, ?, ?, ?, NULL, ?) ON CONFLICT (year, giver_id) DO UPDATE SET "
                "receiver_sealed = excluded.receiver_sealed, assigned_at = excluded.assigned_at, notified_at = NULL",
                (year, giver, sealed, db.now(), prev.get(giver, 0)),
            )
        kind = "draw" if not st["drawn"] else ("reshuffle (everyone)" if body.everyone else "partial reshuffle")
        db.audit(conn, s.admin_name, kind, f"{year}: {len(plan.reshuffled)} of {len(people)} redrawn")
    return {
        "reshuffled": len(plan.reshuffled),
        "hidden_count": plan.hidden_count if st["drawn"] and not body.everyone else 0,
        "total": len(people),
    }


@app.post("/api/years/{year}/notify")
def notify(year: int, body: NotifyIn, s: Session = Depends(current)):
    """Send each participant their own postcard. The caller never sees the content."""
    results = []
    with db.connect() as conn:
        y = _year_or_404(conn, year)
        st = _state(conn, year)
        if not st["in_sync"]:
            raise HTTPException(409, "The participant list changed since the draw. Reshuffle first.")
        rows = conn.execute(
            "SELECT p.giver_id, p.receiver_sealed, p.notified_at, p.notify_count, m.name, m.email, m.lang "
            "FROM pairings p JOIN members m ON m.id = p.giver_id WHERE p.year = ?", (year,)
        ).fetchall()
        if body.member_ids is None:
            rows = [r for r in rows if r["notified_at"] is None]
        else:
            wanted = set(body.member_ids)
            rows = [r for r in rows if r["giver_id"] in wanted]
        names = _names(conn, st["participants"])
        for r in rows:
            receiver = crypto.open_receiver(s.key, year, r["giver_id"], r["receiver_sealed"])
            letter = mailer.Letter(
                giver_name=r["name"], giver_email=r["email"], receiver_name=names[receiver], year=year,
                budget=y["budget"], exchange_date=y["exchange_date"], note=y["note"],
                updated=r["notify_count"] > 0, lang=r["lang"] or mailer.DEFAULT_LANG,
            )
            try:
                mailer.send(letter)
            except Exception as exc:  # report per person, keep going
                results.append({"id": r["giver_id"], "name": r["name"], "ok": False, "error": type(exc).__name__ + ": " + str(exc)[:200]})
                continue
            conn.execute(
                "UPDATE pairings SET notified_at = ?, notify_count = notify_count + 1 WHERE year = ? AND giver_id = ?",
                (db.now(), year, r["giver_id"]),
            )
            results.append({"id": r["giver_id"], "name": r["name"], "ok": True})
        db.audit(conn, s.admin_name, "postcards sent", f"{year}: {sum(x['ok'] for x in results)} ok, "
                 f"{sum(not x['ok'] for x in results)} failed")
    return {"results": results, "mode": mailer.mode()}


@app.post("/api/years/{year}/reveal")
def reveal(year: int, body: RevealIn, s: Session = Depends(current)):
    """Unlock the matches. Requires re-entering the password; always audit-logged."""
    with db.connect() as conn:
        _year_or_404(conn, year)
        if body.password:
            _check_password(conn, s.admin_id, body.password)
        elif s.reauth_until > time.time():
            s.reauth_until = 0.0  # one unlock per fresh Google sign-in
        else:
            raise HTTPException(403, "Re-enter your password or confirm with Google to unlock.")
        pairing = _load_pairing(conn, s.key, year)
        names = _names(conn, set(pairing) | set(pairing.values()))
        db.audit(conn, s.admin_name, "MATCHES REVEALED", str(year))
    pairs = [{"giver": names.get(g, "?"), "receiver": names.get(r, "?")} for g, r in pairing.items()]
    return sorted(pairs, key=lambda p: p["giver"].lower())


@app.get("/api/audit")
def audit_log(s: Session = Depends(current)):
    with db.connect() as conn:
        rows = conn.execute("SELECT at, admin_name, action, detail FROM audit_log ORDER BY id DESC LIMIT 300").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/postcard/preview", response_class=HTMLResponse)
def postcard_preview(updated: bool = False, lang: Literal["hu", "en"] = "hu", s: Session = Depends(current)):
    """Sample postcard with made-up names (never real matches)."""
    return mailer.render_html(mailer.Letter(
        giver_name="Rudolf", giver_email="rudolf@example.com", receiver_name="Mikulásné" if lang == "hu" else "Mrs. Claus",
        year=time.gmtime().tm_year, budget="€30" if lang == "en" else "10 000 Ft",
        exchange_date="24 December, after dinner" if lang == "en" else "december 24., vacsora után",
        note="Handmade gifts earn bonus cookies." if lang == "en" else "A saját kézzel készített ajándékért extra sütemény jár.",
        updated=updated, lang=lang,
    ))


# ─── Frontend ──────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")
