"""Google sign-in (OpenID Connect, authorization-code flow).

Admins are identified by their verified Google e-mail address, which must be
registered on an admin row. Google only proves *who* someone is; it gives us
no secret to decrypt the matches with. So when Google sign-in is enabled the
master key is additionally wrapped with SANTA_SERVER_KEY, a secret that lives
in the server environment, never in the database (see README, "Secrecy").

The id_token is received directly from Google's token endpoint over TLS
using our client secret, so per OpenID Connect Core §3.1.3.7 its signature
check may be skipped; issuer, audience, expiry, nonce and e-mail
verification are still checked.
"""
from __future__ import annotations

import base64
import json
import os
import time
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
REAUTH_MAX_AGE = 120  # seconds: how fresh a sign-in must be to unlock matches


class GoogleAuthError(Exception):
    pass


def client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "")


def enabled() -> bool:
    return all(os.environ.get(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "PUBLIC_URL", "SANTA_SERVER_KEY"))


def redirect_uri() -> str:
    return os.environ["PUBLIC_URL"].rstrip("/") + "/auth/google/callback"


def server_kek() -> bytes:
    raw = base64.b64decode(os.environ["SANTA_SERVER_KEY"])
    if len(raw) != 32:
        raise GoogleAuthError("SANTA_SERVER_KEY must be 32 random bytes, base64-encoded.")
    return raw


def authorization_url(state: str, nonce: str, reauth: bool, login_hint: str = "") -> str:
    params = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "prompt": "select_account",
    }
    if reauth:  # force a fresh sign-in before showing the matches
        params.update(prompt="login", max_age="0")
    if login_hint:
        params["login_hint"] = login_hint
    return f"{AUTH_URL}?{urlencode(params)}"


def _decode_payload(id_token: str) -> dict:
    try:
        payload = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except Exception as exc:  # noqa: BLE001
        raise GoogleAuthError("Malformed id_token") from exc


def exchange_code(code: str) -> str:
    """Swap the authorization code for an id_token (network call)."""
    resp = httpx.post(TOKEN_URL, timeout=10.0, data={
        "code": code,
        "client_id": client_id(),
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "redirect_uri": redirect_uri(),
        "grant_type": "authorization_code",
    })
    if resp.status_code != 200:
        raise GoogleAuthError(f"Google token exchange failed ({resp.status_code})")
    return resp.json()["id_token"]


def verify_claims(id_token: str, nonce: str, require_fresh: bool) -> dict:
    c = _decode_payload(id_token)
    now = time.time()
    if c.get("iss") not in ISSUERS:
        raise GoogleAuthError("Wrong issuer")
    if c.get("aud") != client_id():
        raise GoogleAuthError("Token was not issued for this app")
    if float(c.get("exp", 0)) < now:
        raise GoogleAuthError("Token expired")
    if c.get("nonce") != nonce:
        raise GoogleAuthError("Nonce mismatch")
    if not c.get("email") or c.get("email_verified") not in (True, "true"):
        raise GoogleAuthError("Google account e-mail is not verified")
    if require_fresh and now - float(c.get("auth_time", 0)) > REAUTH_MAX_AGE:
        raise GoogleAuthError("Please sign in again to unlock the matches")
    return c
