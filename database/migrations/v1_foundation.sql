-- ============================================================
-- Turul Academy — Migration v1: Foundation Schema
-- Supabase project: neshzfcetxradwhbmdbb
-- Apply via: Supabase SQL Editor
-- ============================================================

-- ─── CURRICULUM STRUCTURE ────────────────────────────────────

create table public.curriculum_subjects (
  id          uuid primary key default gen_random_uuid(),
  code        text unique not null,       -- e.g. 'HU-NAT-HISTORY-2020'
  name        text not null,              -- English
  name_hu     text not null,              -- Hungarian
  grade_min   int not null,
  grade_max   int not null,
  is_active   boolean default true,
  created_at  timestamptz default now()
);

create table public.curriculum_topics (
  id              uuid primary key default gen_random_uuid(),
  subject_id      uuid not null references public.curriculum_subjects(id),
  nat_id          text unique not null,   -- official NAT topic ID e.g. 'NAT-HIST-7-1.2.3'
  title           text not null,
  title_hu        text not null,
  grade           int not null,
  semester        int check (semester in (1, 2)),
  parent_topic_id uuid references public.curriculum_topics(id),
  order_index     int not null default 0,
  is_active       boolean default true,
  created_at      timestamptz default now()
);

create index idx_topics_subject_grade on public.curriculum_topics(subject_id, grade);
create index idx_topics_nat_id on public.curriculum_topics(nat_id);

-- ─── LESSON CONTENT ──────────────────────────────────────────

create table public.lessons (
  id              uuid primary key default gen_random_uuid(),
  topic_id        uuid not null references public.curriculum_topics(id),
  mode            text not null check (mode in ('text', 'story', 'visual', 'quiz')),
  title           text not null,
  content         jsonb not null default '[]',  -- array of lesson cards
  reading_time_minutes int,
  difficulty      int check (difficulty between 1 and 5),
  generated_by    text default 'ai',        -- 'ai' | 'human'
  reviewed_by     uuid references auth.users(id),
  review_status   text default 'pending'
                  check (review_status in ('pending', 'approved', 'needs_revision', 'rejected')),
  reviewed_at     timestamptz,
  is_active       boolean default false,    -- only active after teacher approval
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),
  unique (topic_id, mode)                   -- one lesson per mode per topic
);

create index idx_lessons_topic on public.lessons(topic_id);
create index idx_lessons_review_status on public.lessons(review_status);

-- ─── QUIZ QUESTIONS ──────────────────────────────────────────

create table public.quiz_questions (
  id              uuid primary key default gen_random_uuid(),
  topic_id        uuid not null references public.curriculum_topics(id),
  lesson_id       uuid references public.lessons(id),
  question_type   text not null check (question_type in ('multiple_choice', 'true_false', 'short_answer')),
  question        text not null,
  options         jsonb,                    -- [{text, is_correct}] for multiple choice
  correct_answer  text,
  explanation     text,                     -- shown after answering
  difficulty      int check (difficulty between 1 and 5),
  is_active       boolean default false,
  created_at      timestamptz default now()
);

create index idx_questions_topic on public.quiz_questions(topic_id);
create index idx_questions_lesson on public.quiz_questions(lesson_id);

-- ─── CURIOSITY LINKS ─────────────────────────────────────────

create table public.curiosity_links (
  id              uuid primary key default gen_random_uuid(),
  from_topic_id   uuid not null references public.curriculum_topics(id),
  to_topic_id     uuid not null references public.curriculum_topics(id),
  link_type       text check (link_type in ('person', 'event', 'invention', 'concept', 'place')),
  title           text not null,
  description     text,
  created_at      timestamptz default now(),
  check (from_topic_id != to_topic_id)
);

-- ─── USER PROFILES ───────────────────────────────────────────

create table public.user_profiles (
  id                  uuid primary key references auth.users(id) on delete cascade,
  role                text default 'student' check (role in ('student', 'teacher', 'reviewer', 'admin')),
  display_name        text,
  grade               int,                  -- for students
  birth_year          int,                  -- for under-13 GDPR detection
  school              text,
  preferred_mode      text check (preferred_mode in ('text', 'story', 'visual', 'quiz')),
  gamification_level  text default 'light' check (gamification_level in ('light', 'full', 'off')),
  accessibility_prefs jsonb default '{}',   -- {font, contrast, text_size, audio}
  language            text default 'hu',
  parent_email        text,                 -- required if birth_year indicates under-13
  parental_consent_at timestamptz,          -- ⚠️ GDPR: required before storing data for under-13
  created_at          timestamptz default now()
);

-- ─── USER SUBJECT ENROLMENT ──────────────────────────────────

create table public.user_subjects (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  subject_id  uuid not null references public.curriculum_subjects(id),
  enrolled_at timestamptz default now(),
  unique (user_id, subject_id)
);

-- ─── LESSON PROGRESS ─────────────────────────────────────────

create table public.lesson_progress (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references auth.users(id) on delete cascade,
  lesson_id           uuid not null references public.lessons(id),
  topic_id            uuid not null references public.curriculum_topics(id),
  status              text default 'not_started'
                      check (status in ('not_started', 'in_progress', 'completed')),
  mode_used           text,
  started_at          timestamptz,
  completed_at        timestamptz,
  time_spent_seconds  int default 0,
  unique (user_id, lesson_id)
);

create index idx_progress_user on public.lesson_progress(user_id);
create index idx_progress_user_topic on public.lesson_progress(user_id, topic_id);

-- ─── QUIZ RESULTS ────────────────────────────────────────────

create table public.quiz_results (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  lesson_id     uuid not null references public.lessons(id),
  topic_id      uuid not null references public.curriculum_topics(id),
  score         int check (score between 0 and 100),
  answers       jsonb not null default '[]', -- [{question_id, answer, is_correct}]
  xp_earned     int default 0,
  completed_at  timestamptz default now()
);

create index idx_quiz_results_user on public.quiz_results(user_id);

-- ─── GAMIFICATION ────────────────────────────────────────────

create table public.user_xp (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid unique not null references auth.users(id) on delete cascade,
  total_xp        int default 0,
  level           int default 1,
  streak_days     int default 0,
  last_activity_date date
);

create table public.user_badges (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  badge_type  text not null,
  badge_data  jsonb default '{}',
  earned_at   timestamptz default now()
);

create table public.daily_activity (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references auth.users(id) on delete cascade,
  date                date not null,
  lessons_completed   int default 0,
  xp_earned           int default 0,
  unique (user_id, date)
);

-- ─── RLS POLICIES ────────────────────────────────────────────

alter table public.curriculum_subjects     enable row level security;
alter table public.curriculum_topics       enable row level security;
alter table public.lessons                 enable row level security;
alter table public.quiz_questions          enable row level security;
alter table public.curiosity_links         enable row level security;
alter table public.user_profiles           enable row level security;
alter table public.user_subjects           enable row level security;
alter table public.lesson_progress         enable row level security;
alter table public.quiz_results            enable row level security;
alter table public.user_xp                 enable row level security;
alter table public.user_badges             enable row level security;
alter table public.daily_activity          enable row level security;

-- Curriculum is public read (no login needed to browse)
create policy "curriculum_subjects_public_read"  on public.curriculum_subjects  for select using (true);
create policy "curriculum_topics_public_read"    on public.curriculum_topics    for select using (is_active = true);
create policy "lessons_public_read"              on public.lessons              for select using (is_active = true);
create policy "quiz_questions_public_read"       on public.quiz_questions       for select using (is_active = true);
create policy "curiosity_links_public_read"      on public.curiosity_links      for select using (true);

-- User data scoped to owner
create policy "user_profiles_own"     on public.user_profiles    for all using (auth.uid() = id);
create policy "user_subjects_own"     on public.user_subjects     for all using (auth.uid() = user_id);
create policy "lesson_progress_own"   on public.lesson_progress   for all using (auth.uid() = user_id);
create policy "quiz_results_own"      on public.quiz_results      for all using (auth.uid() = user_id);
create policy "user_xp_own"           on public.user_xp           for all using (auth.uid() = user_id);
create policy "user_badges_own"       on public.user_badges       for all using (auth.uid() = user_id);
create policy "daily_activity_own"    on public.daily_activity     for all using (auth.uid() = user_id);

-- Admins/reviewers can manage content (service role bypasses RLS)
create policy "lessons_reviewer_update" on public.lessons
  for update using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and role in ('reviewer', 'admin')
    )
  );

-- ─── GRANTS (required from Supabase Oct 2026) ────────────────

grant select on public.curriculum_subjects  to anon, authenticated;
grant select on public.curriculum_topics    to anon, authenticated;
grant select on public.lessons              to anon, authenticated;
grant select on public.quiz_questions       to anon, authenticated;
grant select on public.curiosity_links      to anon, authenticated;

grant select, insert, update, delete on public.user_profiles    to authenticated;
grant select, insert, update, delete on public.user_subjects     to authenticated;
grant select, insert, update, delete on public.lesson_progress   to authenticated;
grant select, insert, update, delete on public.quiz_results      to authenticated;
grant select, insert, update, delete on public.user_xp           to authenticated;
grant select, insert, update, delete on public.user_badges       to authenticated;
grant select, insert, update, delete on public.daily_activity     to authenticated;

grant select, insert, update, delete on all tables in schema public to service_role;
grant usage, select on all sequences in schema public to authenticated, service_role;
