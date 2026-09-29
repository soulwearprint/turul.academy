import { supabase } from './supabase'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

async function getToken(token) {
  if (token) return token
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token ?? null
}

async function headers(token) {
  const t = await getToken(token)
  return t
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${t}` }
    : { 'Content-Type': 'application/json' }
}

async function get(path, token) {
  const h = await headers(token)
  const res = await fetch(`${BASE}${path}`, { headers: h })
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`)
  return res.json()
}

// keepalive: the request survives the page being closed/hidden — used for the final
// study-time flush when a student leaves a lesson.
async function post(path, body, token, { keepalive = false } = {}) {
  const h = await headers(token)
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: h,
    body: JSON.stringify(body),
    keepalive,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => res.status)
    throw new Error(`POST ${path} → ${res.status}: ${msg}`)
  }
  return res.json()
}

async function patch(path, body, token) {
  const h = await headers(token)
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: h,
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PATCH ${path} → ${res.status}`)
  return res.json()
}

async function put(path, body, token) {
  const h = await headers(token)
  const res = await fetch(`${BASE}${path}`, { method: 'PUT', headers: h, body: JSON.stringify(body) })
  if (!res.ok) throw new Error(`PUT ${path} → ${res.status}`)
  return res.json()
}

async function del(path, token) {
  const h = await headers(token)
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE', headers: h })
  if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`)
  return res.json()
}

export const api = {
  curriculum: {
    subjects:       ()                    => get('/api/curriculum/subjects'),
    topics:         (sid, grade)          => get(`/api/curriculum/subjects/${sid}/topics${grade ? `?grade=${grade}` : ''}`),
    topic:          (tid)                 => get(`/api/curriculum/topics/${tid}`),
    curiosityLinks: (tid)                 => get(`/api/curriculum/topics/${tid}/curiosity-links`),
  },
  lessons: {
    get:            (lid, token)          => get(`/api/lessons/${lid}`, token),
    forTopic:       (tid, token)          => get(`/api/lessons/topic/${tid}`, token),
    quiz:           (lid, token)          => get(`/api/lessons/${lid}/quiz`, token),
    updateProgress: (lid, body, token)    => post(`/api/lessons/${lid}/progress`, body, token),
  },
  nat: {
    topics:      (grade, subjectId)   => {
      const q = [grade && `grade=${grade}`, subjectId && `subject_id=${subjectId}`].filter(Boolean).join('&')
      return get(`/api/nat/topics${q ? `?${q}` : ''}`)
    },
    topic:       (tid)                => get(`/api/nat/topics/${tid}`),
    lesson:      (lid)                => get(`/api/nat/lessons/${lid}`),
    topicQuiz:   (tid)                => get(`/api/nat/topics/${tid}/quiz`),
    progress:    (token)             => get('/api/nat/progress/me', token),
    setProgress: (lid, body, token)  => post(`/api/nat/lessons/${lid}/progress`, body, token),
    trackTime:   (lid, body, token)  => post(`/api/nat/lessons/${lid}/progress`, body, token, { keepalive: true }),
    resetLesson: (lid, token)        => del(`/api/nat/lessons/${lid}/progress`, token),
    submitQuiz:  (body, token)       => post('/api/nat/quiz/submit', body, token),
    stats:       (token)             => get('/api/nat/stats/me', token),
    review:      (token)             => get('/api/nat/review/me', token),
  },
  quiz: {
    submit: (body, token) => post('/api/quiz/submit', body, token),
  },
  progress: {
    me:         (token)        => get('/api/progress/me', token),
    subject:    (sid, token)   => get(`/api/progress/me/subject/${sid}`, token),
    badges:     (token)        => get('/api/progress/me/badges', token),
    activity:   (token)        => get('/api/progress/me/activity', token),
    resetAll:   (token)        => del('/api/progress/me?confirm=RESET', token),
  },
  reports: {
    create:   (body, token)    => post('/api/reports', body, token),
    summary:  (token)          => get('/api/reports/summary', token),
    list:     (status, token)  => get(`/api/reports?status=${status}`, token),
    resolve:  (body, token)    => post('/api/reports/resolve', body, token),
    editCard: (body, token)    => put('/api/reports/card', body, token),
    edits:    (token)          => get('/api/reports/edits', token),
    revert:   (editId, token)  => post(`/api/reports/edits/${editId}/revert`, {}, token),
  },
  account: {
    me:       (token)          => get('/api/account/me', token),
    create:   (body, token)    => post('/api/account/me', body, token),
    update:   (body, token)    => patch('/api/account/me', body, token),
    subjects: (token)          => get('/api/account/me/subjects', token),
    enrol:    (sid, token)     => post(`/api/account/me/subjects/${sid}`, {}, token),
  },
}
