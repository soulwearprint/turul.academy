import email
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
        giver = text.split("dear ")[1].split("!")[0]
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
