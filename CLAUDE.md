# Turul Academy — AI Instructions

## What this is
An adaptive learning platform for Hungarian students grades 5-12.
Subjects: History + Physics (launch). NAT-aligned content, multi-modal lessons, teacher-validated.

## URLs
- Frontend: https://turul.academy (Vercel)
- Backend: https://api.turul.academy (Railway)
- Supabase: https://neshzfcetxradwhbmdbb.supabase.co

## Stack
- Frontend: React 18 + Vite + Tailwind (mobile-first PWA)
- Backend: Python 3.11 + FastAPI
- Database: Supabase PostgreSQL (NOT MongoDB)
- Auth: Supabase Auth (JWT)

## Structure
```
turul-academy/
├── frontend/     React + Vite
├── backend/      FastAPI
├── database/     SQL migrations (apply via Supabase SQL Editor)
└── content/      NAT curriculum data + AI generation scripts
```

## Dev workflow
```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in Supabase keys
uvicorn main:app --reload --port 8001

# Frontend
cd frontend && npm install
cp .env.example .env.local  # fill in env vars
npm run dev
```

## Critical rules

### ⚠️ GDPR — under-13 users
- birth_year field in user_profiles detects under-13
- parent_email is REQUIRED before creating profile for under-13
- parental_consent_at must be set before storing ANY learning data for under-13
- Never skip this check. It is enforced in account.py but must be maintained.

### DB migrations
- Only write migrations to database/migrations/
- Always include RLS policies AND explicit GRANTs (see v1_foundation.sql for pattern)
- Naming: v{N}_{description}.sql
- Update MIGRATION_ORDER.md when applying

### Auth pattern
```python
@router.get("/endpoint")
async def handler(user: SupabaseUser = Depends(get_current_user)):
    # user.id, user.email available
```

### Supabase gotchas
- Use `or ""` not `.get(key, "")` for nullable fields (None vs absent)
- httpx client keepalive_expiry <= 15s (Supabase Warp kills idle connections)
- All Supabase REST calls: timeout=7.0
- Always include explicit GRANTs on new tables (required from Oct 2026)

### Content model
- Lesson content is stored as JSONB array of cards in lessons.content
- Each card: {type, content, ...type-specific fields}
- Lessons are inactive (is_active=false) until teacher approves
- One lesson per mode per topic (enforced by unique constraint)

### Scaling warnings (see project memory for full thresholds)
- ~300 concurrent users: review connection pool
- Phase 3 AI features: token budget FIRST, then build
- Under-13 users: GDPR review before public launch
