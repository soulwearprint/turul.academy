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
    for f in sorted((tmp_path / "outbox").glob("*.eml"), key=lambda f: f.stat().st_mtime):
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
    ok(c.put(f"/api/p/{g_token}/wishes", json={"items": [{"text": "Gyapjúzokni", "url": "example.com/zokni"},
                                                            {"text": "Krimi"}]}))
    wishes = ok(c.get(f"/api/p/{token}"))["giftee"]["wishes"]
    assert [w["text"] for w in wishes] == ["Gyapjúzokni", "Krimi"] and wishes[0]["url"] == "https://example.com/zokni"
    assert c.put(f"/api/p/{token}/wishes", json={"items": [{"text": f"x{i}"} for i in range(6)]}).status_code == 422

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
