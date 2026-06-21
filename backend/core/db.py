from typing import Optional, Union
import httpx
from .config import settings
from .auth import http

SUPABASE_HEADERS_ANON = {
    "apikey": settings.supabase_anon_key,
    "Content-Type": "application/json",
}

SUPABASE_HEADERS_SERVICE = {
    "apikey": settings.supabase_service_role_key,
    "Authorization": f"Bearer {settings.supabase_service_role_key}",
    "Content-Type": "application/json",
}


def rest_url(table: str) -> str:
    return f"{settings.supabase_url}/rest/v1/{table}"


def rpc_url(fn: str) -> str:
    return f"{settings.supabase_url}/rest/v1/rpc/{fn}"


async def db_get(table: str, params: dict, *, user_token: Optional[str] = None) -> list:
    """GET rows from a table. Uses user token for RLS-scoped reads."""
    headers = {**SUPABASE_HEADERS_ANON}
    if user_token:
        headers["Authorization"] = f"Bearer {user_token}"

    resp = await http().get(rest_url(table), headers=headers, params=params, timeout=7.0)
    resp.raise_for_status()
    return resp.json()


async def db_post(table: str, payload: Union[dict, list], *, service: bool = False) -> dict:
    """INSERT row(s). Use service=True to bypass RLS (admin operations)."""
    headers = SUPABASE_HEADERS_SERVICE if service else SUPABASE_HEADERS_ANON
    resp = await http().post(
        rest_url(table),
        headers={**headers, "Prefer": "return=representation"},
        json=payload,
        timeout=7.0,
    )
    resp.raise_for_status()
    return resp.json()


async def db_patch(table: str, params: dict, payload: dict, *, user_token: Optional[str] = None, service: bool = False) -> dict:
    """UPDATE rows matching params. Use service=True to bypass RLS (admin operations)."""
    base = SUPABASE_HEADERS_SERVICE if service else SUPABASE_HEADERS_ANON
    headers = {**base, "Prefer": "return=representation"}
    if user_token and not service:
        headers["Authorization"] = f"Bearer {user_token}"

    resp = await http().patch(
        rest_url(table), headers=headers, params=params, json=payload, timeout=7.0
    )
    resp.raise_for_status()
    return resp.json()
