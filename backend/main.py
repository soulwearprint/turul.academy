from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import curriculum, lessons, quiz, progress, account, nat

app = FastAPI(title="Turul Academy API", version="0.1.0")

# CORS — tighten in production to ["https://turul.academy"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if True else ["https://turul.academy"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(curriculum.router)
app.include_router(lessons.router)
app.include_router(quiz.router)
app.include_router(progress.router)
app.include_router(account.router)
app.include_router(nat.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/healthz")
async def healthz():
    """Readiness check — verifies Supabase connectivity."""
    from core.db import db_get
    try:
        await db_get("curriculum_subjects", {"select": "id", "limit": "1"})
        return {"status": "ok", "supabase": "reachable"}
    except Exception as e:
        return {"status": "degraded", "supabase": str(e)}
