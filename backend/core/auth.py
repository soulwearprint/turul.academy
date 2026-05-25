from typing import Optional
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dataclasses import dataclass
from .config import settings

security = HTTPBearer()

# Shared httpx client — keepalive_expiry <= 15s to avoid Supabase Warp stale socket issues
_http_client: Optional[httpx.AsyncClient] = None


def http() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(keepalive_expiry=15),
        )
    return _http_client


@dataclass
class SupabaseUser:
    id: str
    email: str
    role: str = "student"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> SupabaseUser:
    """Verify Supabase JWT and return the authenticated user."""
    token = credentials.credentials
    try:
        resp = await http().get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_anon_key,
            },
        )
    except httpx.TransportError as e:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    data = resp.json()
    return SupabaseUser(
        id=data["id"],
        email=data.get("email", ""),
    )
