import email
import email.utils
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SANTA_DB", str(tmp_path / "s.db"))
    monkeypatch.setenv("SANTA_OUTBOX", str(tmp_path / "outbox"))
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("SANTA_DIGEST_SCHEDULER", "0")  # tests call run_digest() themselves
    monkeypatch.setenv("SANTA_SERVER_KEY_FILE", str(tmp_path / "server.key"))
    from app import main
    main._sessions.clear()
    with TestClient(main.app) as c:
        yield c


def ok(r):
    assert r.status_code < 300, r.text
    return r.json()


def add_people(c, names):
    return {n: ok(c.post("/api/members", json={"name": n, "email": f"{n.lower()}@fam.test"}))["id"] for n in names}


def receivers_from_outbox(tmp_path):
    """Parse giver -> receiver out of the written postcards (test-only peek)."""
    out = {}
    for f in (tmp_path / "outbox").glob("*.eml"):
        if "_ideas_" in f.name or "_invite_" in f.name:
            continue
        msg = email.message_from_bytes(f.read_bytes())
        text = msg.get_payload()[0].get_payload(decode=True).decode()
        giver = email.utils.parseaddr(msg["To"])[0]
        out[giver] = text.split("★ ")[1].split(" ★")[0]
    return out


def test_full_flow(client, tmp_path):
    c = client
    assert ok(c.get("/api/status"))["setup_done"] is False
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    assert c.post("/api/setup", json={"name": "X", "password": "secret1"}).status_code == 409

    ids = add_people(c, ["Anna", "Bela", "Csilla", "Dani", "Eva"])
    ok(c.post("/api/years", json={"year": 2026}))
    y = ok(c.get("/api/years/2026"))
    assert len(y["participants"]) == 5 and not y["drawn"]

    ok(c.post("/api/years/2026/draw", json={}))
    # second draw requires explicit confirmation
    assert c.post("/api/years/2026/draw", json={}).status_code == 409

    res = ok(c.post("/api/years/2026/notify", json={}))
    assert len(res["results"]) == 5 and all(r["ok"] for r in res["results"])
    pairs = receivers_from_outbox(tmp_path)
    assert set(pairs) == set(pairs.values()) == {"Anna", "Bela", "Csilla", "Dani", "Eva"}
    assert all(g != r for g, r in pairs.items())
    # each e-mail goes to exactly one person
    for f in (tmp_path / "outbox").glob("*.eml"):
        msg = email.message_from_bytes(f.read_bytes())
        assert "," not in msg["To"] and msg["Cc"] is None and msg["Bcc"] is None
        assert "★" not in msg["Subject"]

    # reveal needs the right password and is logged
    assert c.post("/api/years/2026/reveal", json={"password": "nope"}).status_code == 403
    revealed = ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))
    assert {p["giver"]: p["receiver"] for p in revealed} == pairs
    assert any(a["action"] == "MATCHES REVEALED" for a in ok(c.get("/api/audit")))

    # list changes: Eva leaves, Feri joins -> notify blocked until reshuffle
    feri = add_people(c, ["Feri"])["Feri"]
    new_list = [ids[n] for n in ["Anna", "Bela", "Csilla", "Dani"]] + [feri]
    assert ok(c.put("/api/years/2026/participants", json={"member_ids": new_list}))["needs_reshuffle"]
    y = ok(c.get("/api/years/2026"))
    assert [p["name"] for p in y["added"]] == ["Feri"] and [p["name"] for p in y["removed"]] == ["Eva"]
    assert c.post("/api/years/2026/notify", json={}).status_code == 409
    assert c.post("/api/years/2026/draw", json={"selected_ids": []}).status_code == 409  # no confirm

    res = ok(c.post("/api/years/2026/draw", json={"selected_ids": [], "confirm": True}))
    assert res["reshuffled"] >= 1
    after = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))}
    assert set(after) == set(after.values()) == {"Anna", "Bela", "Csilla", "Dani", "Feri"}
    y = ok(c.get("/api/years/2026"))
    assert y["in_sync"]
    pending = [p["name"] for p in y["participants"] if not p["notified_at"]]
    assert "Feri" in pending and len(pending) == res["reshuffled"]


def test_admin_limits_and_encryption(client, tmp_path):
    c = client
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    for i in range(4):
        ok(c.post("/api/admins", json={"name": f"A{i}", "password": "secret1"}))
    assert c.post("/api/admins", json={"name": "A9", "password": "secret1"}).status_code == 409
    admins = ok(c.get("/api/admins"))
    first = next(a for a in admins if a["slot"] == 1)
    assert c.delete(f"/api/admins/{first['id']}").status_code == 400

    add_people(c, ["Anna", "Bela", "Csilla"])
    ok(c.post("/api/years", json={"year": 2026}))
    ok(c.post("/api/years/2026/draw", json={}))

    # a second admin can log in and unlock with their own password
    c.post("/api/logout")
    assert c.get("/api/members").status_code == 401
    ok(c.post("/api/login", json={"name": "A2", "password": "secret1"}))
    assert len(ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))) == 3

    # the DB file contains no member ids in clear for the pairings
    import sqlite3
    rows = sqlite3.connect(tmp_path / "s.db").execute("SELECT receiver_sealed FROM pairings").fetchall()
    assert all(len(r[0]) > 20 and not r[0].isdigit() for r in rows)


def test_new_year_copies_previous_list(client):
    c = client
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    ids = add_people(c, ["Anna", "Bela", "Csilla"])
    ok(c.post("/api/years", json={"year": 2025}))
    ok(c.put("/api/years/2025/participants", json={"member_ids": [ids["Anna"], ids["Bela"]]}))
    ok(c.post("/api/years", json={"year": 2026}))
    assert {p["name"] for p in ok(c.get("/api/years/2026"))["participants"]} == {"Anna", "Bela"}


def test_rules_language_and_no_repeat(client, tmp_path):
    c = client
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    names = ["Anna", "Bela", "Csilla", "Dani", "Eva", "Feri", "Gabi", "Hanna", "Ivan", "Jozsi", "Kata"]
    ids = add_people(c, names)
    ok(c.put(f"/api/members/{ids['Kata']}", json={"name": "Kata", "email": "kata@fam.test", "lang": "en"}))
    couples = [("Anna", "Bela"), ("Csilla", "Dani"), ("Eva", "Feri"), ("Gabi", "Hanna")]
    for a, b in couples:
        ok(c.post("/api/exclusions", json={"a_id": ids[a], "b_id": ids[b]}))
    assert len(ok(c.get("/api/exclusions"))) == 4

    ok(c.post("/api/years", json={"year": 2025}))
    ok(c.post("/api/years/2025/draw", json={}))
    y25 = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2025/reveal", json={"password": "secret1"}))}
    ok(c.post("/api/years", json={"year": 2026}))
    assert ok(c.get("/api/years/2026"))["avoid_repeat"] is True
    ok(c.post("/api/years/2026/draw", json={}))
    y26 = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))}

    for pairs in (y25, y26):
        for a, b in couples:
            assert pairs[a] != b and pairs[b] != a
    assert all(y26[g] != y25[g] for g in names)

    # Hungarian by default, English for Kata
    ok(c.post("/api/years/2026/notify", json={}))
    for f in (tmp_path / "outbox").glob("2026_*.eml"):
        msg = email.message_from_bytes(f.read_bytes())
        text = msg.get_payload()[0].get_payload(decode=True).decode()
        if "kata@" in msg["To"]:
            assert "Ho ho ho, dear Kata!" in text and "Santa Claus" in text
        else:
            assert "Ho-ho-ho, kedves" in text and "Mikulás" in text

    # adding an exclusion after the draw forces a redraw of whoever breaks it
    giver = next(g for g in names if g != "Kata" and y26[g] != "Kata" and g not in dict(couples) and g not in dict(couples).values())
    ok(c.post("/api/exclusions", json={"a_id": ids[giver], "b_id": ids[y26[giver]]}))
    ok(c.post("/api/years/2026/draw", json={"selected_ids": [], "confirm": True}))
    after = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))}
    assert after[giver] != y26[giver]


def test_impossible_rules_are_reported(client):
    c = client
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    ids = add_people(c, ["Anna", "Bela", "Csilla"])
    ok(c.post("/api/exclusions", json={"a_id": ids["Anna"], "b_id": ids["Bela"]}))
    ok(c.post("/api/exclusions", json={"a_id": ids["Anna"], "b_id": ids["Csilla"]}))
    ok(c.post("/api/years", json={"year": 2026}))
    r = c.post("/api/years/2026/draw", json={})
    assert r.status_code == 422 and "impossible" in r.json()["detail"]


def _fake_google(monkeypatch, email_addr, fresh=True):
    import base64, json, time as _t
    from app import google_auth

    def fake_exchange(code):
        nonce = code  # the test passes the nonce as the "code"
        now = _t.time()
        claims = {"iss": "https://accounts.google.com", "aud": "cid", "exp": now + 300, "nonce": nonce,
                  "email": email_addr, "email_verified": True, "given_name": "Gmum",
                  "auth_time": now if fresh else now - 3600}
        body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        return f"x.{body}.y"
    monkeypatch.setattr(google_auth, "exchange_code", fake_exchange)


def _google_round_trip(c, purpose="login", year=0):
    from urllib.parse import parse_qs, urlparse
    r = c.get(f"/auth/google/start?purpose={purpose}&year={year}", follow_redirects=False)
    assert r.status_code in (302, 307), r.text
    q = parse_qs(urlparse(r.headers["location"]).query)
    if purpose == "reveal":
        assert q["prompt"] == ["login"] and q["max_age"] == ["0"]
    return c.get(f"/auth/google/callback?state={q['state'][0]}&code={q['nonce'][0]}", follow_redirects=False)


def test_google_sign_in(client, monkeypatch):
    import base64, os as _os
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "sec")
    monkeypatch.setenv("PUBLIC_URL", "http://testserver")
    monkeypatch.setenv("SANTA_SERVER_KEY", base64.b64encode(_os.urandom(32)).decode())
    monkeypatch.setenv("SANTA_FIRST_ADMIN_EMAIL", "mum@gmail.com")
    c = client

    # password setup is blocked when a first admin e-mail is configured
    assert c.post("/api/setup", json={"name": "X", "password": "secret1"}).status_code == 403
    # a stranger cannot claim the first-admin slot
    _fake_google(monkeypatch, "stranger@gmail.com")
    assert "#error=" in _google_round_trip(c).headers["location"]

    _fake_google(monkeypatch, "mum@gmail.com")
    r = _google_round_trip(c)
    assert r.headers["location"] == "/"
    st = ok(c.get("/api/status"))
    assert st["logged_in"] and st["admin"]["google_email"] == "mum@gmail.com" and not st["admin"]["has_password"]

    add_people(c, ["Anna", "Bela", "Csilla"])
    ok(c.post("/api/years", json={"year": 2026}))
    ok(c.post("/api/years/2026/draw", json={}))

    # unlock requires a fresh Google sign-in, which is good for exactly one unlock
    assert c.post("/api/years/2026/reveal", json={}).status_code == 403
    _fake_google(monkeypatch, "mum@gmail.com", fresh=False)
    assert "#error=" in _google_round_trip(c, "reveal", 2026).headers["location"]
    _fake_google(monkeypatch, "mum@gmail.com")
    assert _google_round_trip(c, "reveal", 2026).headers["location"] == "/#reveal=2026"
    assert len(ok(c.post("/api/years/2026/reveal", json={}))) == 3
    assert c.post("/api/years/2026/reveal", json={}).status_code == 403

    # a second admin added by Google e-mail can sign in and work with the draw
    ok(c.post("/api/admins", json={"name": "Dad", "google_email": "dad@gmail.com"}))
    c.post("/api/logout")
    _fake_google(monkeypatch, "dad@gmail.com")
    assert _google_round_trip(c).headers["location"] == "/"
    assert len(ok(c.post("/api/years/2026/notify", json={}))["results"]) == 3
    # non-admin Google accounts are rejected and logged
    c.post("/api/logout")
    _fake_google(monkeypatch, "cousin@gmail.com")
    assert "not%20an%20admin" in _google_round_trip(c).headers["location"]


def test_google_setup_needs_configured_first_admin(client, monkeypatch):
    import base64, os as _os
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "sec")
    monkeypatch.setenv("PUBLIC_URL", "http://testserver")
    monkeypatch.setenv("SANTA_SERVER_KEY", base64.b64encode(_os.urandom(32)).decode())
    monkeypatch.delenv("SANTA_FIRST_ADMIN_EMAIL", raising=False)
    _fake_google(monkeypatch, "anyone@gmail.com")
    assert "#error=" in _google_round_trip(client).headers["location"]
    assert ok(client.get("/api/status"))["setup_done"] is False
    # password setup still works, and the password admin can then add Google admins
    ok(client.post("/api/setup", json={"name": "Mom", "password": "secret1", "google_email": "anyone@gmail.com"}))
    client.post("/api/logout")
    assert _google_round_trip(client).headers["location"] == "/"


def _links_from_outbox(tmp_path):
    """giver name -> (personal page token, receiver name), parsed from the newest cards."""
    out = {}
    cards = [f for f in (tmp_path / "outbox").glob("*.eml") if "_ideas_" not in f.name and "_invite_" not in f.name]
    for f in sorted(cards, key=lambda f: f.stat().st_mtime):
        msg = email.message_from_bytes(f.read_bytes())
        text = msg.get_payload()[0].get_payload(decode=True).decode()
        giver = email.utils.parseaddr(msg["To"])[0]
        token = text.split("/p/")[1].split()[0].split("#")[0]
        out[giver] = (token, text.split("★ ")[1].split(" ★")[0])
    return out


def test_participant_page_wishes_and_language(client, tmp_path):
    c = client
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    ids = add_people(c, ["Anna", "Bela", "Csilla", "Dani"])
    ok(c.post("/api/years", json={"year": 2026}))
    ok(c.put("/api/years/2026", json={"budget": "10 000 Ft", "exchange_date": "dec. 24.", "note": ""}))
    ok(c.post("/api/years/2026/draw", json={}))
    ok(c.post("/api/years/2026/notify", json={}))
    links = _links_from_outbox(tmp_path)
    c.post("/api/logout")  # participants are not logged in

    # the card links to the page; HTML card has the button and a language link
    html = next((tmp_path / "outbox").glob("*.eml")).read_text(errors="ignore")
    assert "/p/" in html and "#lang" in html

    token, giftee = links["Anna"]
    page = ok(c.get(f"/api/p/{token}"))
    assert page["name"] == "Anna" and page["giftee"]["name"] == giftee and page["budget"] == "10 000 Ft"
    r = c.get(f"/p/{token}")
    assert r.status_code == 200 and r.headers["referrer-policy"] == "no-referrer"

    # giftee adds wishes -> Anna sees them on her page
    g_token = links[giftee][0]
    add_wish(c, g_token, "Gyapjúzokni", "example.com/zokni")
    add_wish(c, g_token, "Krimi")
    wishes = ok(c.get(f"/api/p/{token}"))["giftee"]["wishes"]
    assert [w["text"] for w in wishes] == ["Gyapjúzokni", "Krimi"] and wishes[0]["url"] == "https://example.com/zokni"
    for i in range(5):
        add_wish(c, token, f"x{i}")
    assert c.post(f"/api/p/{token}/wishes", json={"text": "x5"}).status_code == 422

    # switching language (and resending) works without login
    ok(c.put(f"/api/p/{token}/lang", json={"lang": "en", "resend": True}))
    assert ok(c.get(f"/api/p/{token}"))["lang"] == "en"
    card = (tmp_path / "outbox" / "2026_anna_fam_test.eml").read_bytes()
    assert b"Ho ho ho, dear Anna" in email.message_from_bytes(card).get_payload()[0].get_payload(decode=True)

    # bad tokens get nothing; the DB holds no usable token
    assert c.get("/api/p/not-a-real-token").status_code == 404
    import sqlite3
    db_rows = sqlite3.connect(tmp_path / "s.db").execute("SELECT link_id FROM participant_links").fetchall()
    assert token not in {r[0] for r in db_rows}

    # admin sees wish counts; a reshuffle retires stale links
    ok(c.post("/api/login", json={"name": "Mom", "password": "secret1"}))
    counts = {p["name"]: p["wishes"] for p in ok(c.get("/api/years/2026"))["participants"]}
    assert counts[giftee] == 2
    ok(c.post("/api/years/2026/draw", json={"everyone": True, "confirm": True}))
    assert c.get(f"/api/p/{token}").status_code == 404
    # wishes survive the reshuffle
    ok(c.post("/api/years/2026/notify", json={}))
    new_links = _links_from_outbox(tmp_path)
    who_has_giftee = next(n for n, (_, r) in new_links.items() if r == giftee)
    assert len(ok(c.get(f"/api/p/{new_links[who_has_giftee][0]}"))["giftee"]["wishes"]) == 2


def _body(path):
    import email.policy
    msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    return msg, msg.get_body(("plain",)).get_content()


def _token_in(text):
    return text.split("/p/")[1].split()[0].split("#")[0]


def add_wish(c, token, text, url=""):
    return ok(c.post(f"/api/p/{token}/wishes", json={"text": text, "url": url}))["my_wishes"]


def _wish_id(c, token, text):
    return next(w["id"] for w in ok(c.get(f"/api/p/{token}"))["my_wishes"] if w["text"] == text)


def _cards(out):
    cards = {}
    for f in out.glob("2026_*.eml"):
        if "_invite_" in f.name or "_ideas_" in f.name:
            continue
        m, t = _body(f)
        cards[email.utils.parseaddr(m["To"])[0]] = (t, _token_in(t))
    return cards


def _digest():
    from app import main
    return main.run_digest()


def test_invitation_then_draw_then_daily_digest(client, tmp_path):
    c = client
    out = tmp_path / "outbox"
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    add_people(c, ["Anna", "Bela", "Csilla", "Dani"])
    ok(c.post("/api/years", json={"year": 2026}))
    ok(c.put("/api/years/2026", json={"budget": "10 000 Ft", "exchange_date": "", "note": ""}))

    # 1) pre-draw invitations: one per person, budget in it, no match anywhere
    res = ok(c.post("/api/years/2026/invite", json={}))
    assert len(res["results"]) == 4 and all(r["ok"] for r in res["results"])
    assert ok(c.post("/api/years/2026/invite", json={}))["results"] == []  # nobody re-invited by default
    invites = {email.utils.parseaddr(_body(f)[0]["To"])[0]: _token_in(_body(f)[1]) for f in out.glob("2026_invite_*.eml")}
    msg, text = _body(out / "2026_invite_csilla_fam_test.eml")
    assert "10 000 Ft" in text and "★" not in text and "Mit kérnél" in msg["Subject"]
    assert all(p["invited"] for p in ok(c.get("/api/years/2026"))["participants"])

    # invitation page: ideas editable, freely removable (nothing sent yet), no giftee
    page = ok(c.get(f"/api/p/{invites['Csilla']}"))
    assert page["giftee"] is None and page["drawn"] is False
    add_wish(c, invites["Csilla"], "Puzzle 1000 db")
    add_wish(c, invites["Csilla"], "Elírás")
    ok(c.delete(f"/api/p/{invites['Csilla']}/wishes/{_wish_id(c, invites['Csilla'], 'Elírás')}"))
    assert ok(c.get("/api/digest"))["pending"] == 0  # nobody to tell before the draw

    # 2) draw + postcards: Csilla's Secret Santa sees her idea directly on the card -> now "sent"
    ok(c.post("/api/years/2026/draw", json={}))
    ok(c.post("/api/years/2026/notify", json={}))
    cards = _cards(out)
    santa_of_csilla = next(n for n, (t, _) in cards.items() if "★ Csilla ★" in t)
    assert "Puzzle 1000 db" in cards[santa_of_csilla][0] and "Elírás" not in cards[santa_of_csilla][0]
    assert c.get(f"/api/p/{invites['Csilla']}").status_code == 404  # replaced by the postcard link
    c.post("/api/logout")
    tok = cards["Csilla"][1]
    puzzle = _wish_id(c, tok, "Puzzle 1000 db")
    assert next(w for w in ok(c.get(f"/api/p/{tok}"))["my_wishes"] if w["id"] == puzzle)["sent"] is True

    # 3) sent ideas can't be deleted, only marked obsolete; unsent ones can't be marked, only deleted
    assert c.delete(f"/api/p/{tok}/wishes/{puzzle}").status_code == 409
    add_wish(c, tok, "Társasjáték")
    add_wish(c, tok, "Sál")
    sal = _wish_id(c, tok, "Sál")
    assert c.post(f"/api/p/{tok}/wishes/{sal}/obsolete", json={"obsolete": True}).status_code == 409
    ok(c.delete(f"/api/p/{tok}/wishes/{sal}"))  # never reached the giver: silently gone
    ok(c.post(f"/api/p/{tok}/wishes/{puzzle}/obsolete", json={"obsolete": True, "reason": "got_it"}))

    # no e-mail per save: everything waits for the digest, one queued entry
    assert not list(out.glob("2026_ideas_*.eml"))
    ok(c.post("/api/login", json={"name": "Mom", "password": "secret1"}))
    assert ok(c.get("/api/digest"))["pending"] == 1
    c.post("/api/logout")

    # the giver's live page shows the obsolete idea struck through, with its reason
    giver_view = ok(c.get(f"/api/p/{cards[santa_of_csilla][1]}"))["giftee"]["wishes"]
    assert {(w["text"], w["obsolete"], w["reason"]) for w in giver_view} == {("Puzzle 1000 db", True, "got_it"), ("Társasjáték", False, "")}

    # 4) one digest e-mail: new = Társasjáték, gone = Puzzle (reason), Sál never mentioned
    assert _digest() == {"sent": 1, "failed": 0}
    (notice,) = out.glob("2026_ideas_*.eml")
    msg, text = _body(notice)
    assert email.utils.parseaddr(msg["To"])[0] == santa_of_csilla and "Csilla" not in msg["Subject"]
    new_part = text.split("Új ötletek:")[1].split("\n\n")[0]
    gone_part = text.split("Már nem aktuális:")[1].split("\n\n")[0]
    assert "Társasjáték" in new_part and "Puzzle" in gone_part and "már megkapta" in gone_part
    assert "Sál" not in text and "10 000 Ft" in text
    # nothing new -> nothing more
    notice.unlink()
    assert _digest() == {"sent": 0, "failed": 0} and not list(out.glob("2026_ideas_*.eml"))

    # restoring an obsolete idea the giver was told about comes back as "new"
    ok(c.post(f"/api/p/{tok}/wishes/{puzzle}/obsolete", json={"obsolete": False}))
    assert _digest()["sent"] == 1
    assert "Puzzle" in _body(next(out.glob("2026_ideas_*.eml")))[1].split("Új ötletek:")[1].split("\n\n")[0]
    next(out.glob("2026_ideas_*.eml")).unlink()

    # 5) after a full reshuffle the new Secret Santa starts fresh: ideas are unsent again,
    #    obsolete ones dropped, and the digest goes to the NEW giver
    ok(c.post(f"/api/p/{tok}/wishes/{puzzle}/obsolete", json={"obsolete": True, "reason": "mistake"}))
    ok(c.post("/api/login", json={"name": "Mom", "password": "secret1"}))
    ok(c.post("/api/years/2026/draw", json={"everyone": True, "confirm": True}))
    ok(c.post("/api/years/2026/notify", json={}))
    new_cards = _cards(out)
    new_santa = next(n for n, (t, _) in new_cards.items() if "★ Csilla ★" in t)
    new_tok = new_cards["Csilla"][1]
    c.post("/api/logout")
    mine = ok(c.get(f"/api/p/{new_tok}"))["my_wishes"]
    if new_santa != santa_of_csilla:
        assert [w["text"] for w in mine] == ["Társasjáték"]  # obsolete Puzzle dropped for the new giver
    add_wish(c, new_tok, "Kesztyű")
    _digest()
    notices = list(out.glob("2026_ideas_*.eml"))
    assert len(notices) == 1 and email.utils.parseaddr(_body(notices[0])[0]["To"])[0] == new_santa


def test_invited_person_without_card_still_reaches_their_santa(client, tmp_path):
    """Giver got a card, the receiver still only has the invitation link."""
    c = client
    out = tmp_path / "outbox"
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    ids = add_people(c, ["Anna", "Bela", "Csilla"])
    ok(c.post("/api/years", json={"year": 2026}))
    ok(c.post("/api/years/2026/invite", json={}))
    inv = {email.utils.parseaddr(_body(f)[0]["To"])[0]: _token_in(_body(f)[1]) for f in out.glob("2026_invite_*.eml")}
    ok(c.post("/api/years/2026/draw", json={}))
    pairs = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))}
    santa_of_anna = next(g for g, r in pairs.items() if r == "Anna")
    ok(c.post("/api/years/2026/notify", json={"member_ids": [ids[santa_of_anna]]}))  # only Anna's Santa notified
    assert ok(c.get(f"/api/p/{inv['Anna']}"))["giftee"] is None  # Anna still on her invitation link
    add_wish(c, inv["Anna"], "Bögre")
    assert _digest()["sent"] == 1
    notices = list(out.glob("2026_ideas_*.eml"))
    assert len(notices) == 1 and email.utils.parseaddr(_body(notices[0])[0]["To"])[0] == santa_of_anna


def test_digest_schedule(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    monkeypatch.setenv("SANTA_DB", str(tmp_path / "d.db"))
    from app import db, main
    db.init()
    budapest_17 = datetime(2026, 12, 1, 16, 0, tzinfo=timezone.utc)   # 17:00 in Budapest (CET)
    budapest_18 = datetime(2026, 12, 1, 17, 5, tzinfo=timezone.utc)   # 18:05
    assert not main._digest_due(budapest_17)
    assert main._digest_due(budapest_18)
    with db.connect() as conn:
        db.set_setting(conn, "last_digest_at", "2026-12-01T17:06:00+00:00")
    assert not main._digest_due(datetime(2026, 12, 1, 20, 0, tzinfo=timezone.utc))  # already ran today
    assert main._digest_due(datetime(2026, 12, 2, 17, 1, tzinfo=timezone.utc))      # next day


def test_people_without_email_use_a_helper(client, tmp_path):
    c = client
    out = tmp_path / "outbox"
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    ids = add_people(c, ["Anya", "Apa", "Nagymama"])
    # no e-mail and no helper -> refused; helper must have an e-mail of their own
    assert c.post("/api/members", json={"name": "Peti", "email": ""}).status_code == 422
    peti = ok(c.post("/api/members", json={"name": "Peti", "email": "", "helper_id": ids["Anya"]}))["id"]
    assert c.post("/api/members", json={"name": "Baba", "email": "", "helper_id": peti}).status_code == 422
    # a helper can't drop their own e-mail while helping someone
    assert c.put(f"/api/members/{ids['Anya']}", json={"name": "Anya", "email": "", "helper_id": ids["Apa"]}).status_code == 422

    ok(c.post("/api/years", json={"year": 2026}))
    ok(c.put("/api/years/2026", json={"budget": "10 000 Ft", "exchange_date": "", "note": ""}))
    ok(c.post("/api/years/2026/invite", json={}))
    inv = out / "2026_invite_anya_fam_test_for_Peti.eml"
    msg, text = _body(inv)
    assert email.utils.parseaddr(msg["To"]) == ("Anya", "anya@fam.test")
    assert "Peti nevében" in text and "kedves Peti" in text

    for seed in range(15):  # Peti must never draw his helper (Anya would learn her own Secret Santa)
        ok(c.post("/api/years/2026/draw", json={"everyone": True, "confirm": True}))
        pairs = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))}
        assert pairs["Peti"] != "Anya"
    ok(c.post("/api/years/2026/notify", json={}))
    card = out / "2026_anya_fam_test_for_Peti.eml"
    msg, text = _body(card)
    assert email.utils.parseaddr(msg["To"])[1] == "anya@fam.test"
    assert f"★ {pairs['Peti']} ★" in text and "Peti nevében" in text
    # Anya's own card is a separate file and message
    assert (out / "2026_anya_fam_test.eml").exists()

    # Peti's page (opened by Anya) says it is managed by the helper
    c.post("/api/logout")
    page = ok(c.get(f"/api/p/{_token_in(text)}"))
    assert page["name"] == "Peti" and page["helper"] == "Anya"


def test_fixed_pairs(client):
    c = client
    ok(c.post("/api/setup", json={"name": "Mom", "password": "secret1"}))
    ids = add_people(c, ["Anna", "Bela", "Csilla", "Dani", "Eva", "Nagymama", "Peti"])
    ok(c.post("/api/years", json={"year": 2026}))
    ok(c.post("/api/years/2026/fixed", json={"giver_id": ids["Nagymama"], "receiver_id": ids["Peti"]}))
    assert c.post("/api/years/2026/fixed", json={"giver_id": ids["Anna"], "receiver_id": ids["Peti"]}).status_code == 409
    assert c.post("/api/years/2026/fixed", json={"giver_id": ids["Anna"], "receiver_id": ids["Anna"]}).status_code == 422
    assert [f["giver"] for f in ok(c.get("/api/years/2026/fixed"))] == ["Nagymama"]
    # even an exclusion between them is overridden by the fixed pair
    ok(c.post("/api/exclusions", json={"a_id": ids["Nagymama"], "b_id": ids["Peti"]}))
    for _ in range(20):
        ok(c.post("/api/years/2026/draw", json={"everyone": True, "confirm": True}))
        pairs = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))}
        assert pairs["Nagymama"] == "Peti"
        assert list(pairs.values()).count("Peti") == 1
    # a fixed pair added after the draw is applied at the next (partial) reshuffle
    ok(c.post("/api/years/2026/fixed", json={"giver_id": ids["Anna"], "receiver_id": ids["Bela"]}))
    ok(c.post("/api/years/2026/draw", json={"selected_ids": [], "confirm": True}))
    pairs = {p["giver"]: p["receiver"] for p in ok(c.post("/api/years/2026/reveal", json={"password": "secret1"}))}
    assert pairs["Anna"] == "Bela" and pairs["Nagymama"] == "Peti"
    ok(c.delete(f"/api/years/2026/fixed/{ids['Anna']}"))
    assert len(ok(c.get("/api/years/2026/fixed"))) == 1
