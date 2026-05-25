import { supabase } from './supabase'

const BASE = import.meta.env.VITE_BACKEND_URL || ''

async function authHeader() {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return {}
  return { Authorization: `Bearer ${session.access_token}` }
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: await authHeader() })
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeader()) },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`)
  return res.json()
}

async function patch(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...(await authHeader()) },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PATCH ${path} → ${res.status}`)
  return res.json()
}

export const api = {
  curriculum: {
    subjects:       ()           => get('/api/curriculum/subjects'),
    topics:         (sid, grade) => get(`/api/curriculum/subjects/${sid}/topics${grade ? `?grade=${grade}` : ''}`),
    topic:          (tid)        => get(`/api/curriculum/topics/${tid}`),
    curiosityLinks: (tid)        => get(`/api/curriculum/topics/${tid}/curiosity-links`),
  },
  lessons: {
    get:            (lid)        => get(`/api/lessons/${lid}`),
    forTopic:       (tid)        => get(`/api/lessons/topic/${tid}`),
    quiz:           (lid)        => get(`/api/lessons/${lid}/quiz`),
    updateProgress: (lid, body)  => post(`/api/lessons/${lid}/progress`, body),
  },
  quiz: {
    submit: (body) => post('/api/quiz/submit', body),
  },
  progress: {
    me:         ()    => get('/api/progress/me'),
    subject:    (sid) => get(`/api/progress/me/subject/${sid}`),
  },
  account: {
    me:            ()       => get('/api/account/me'),
    create:        (body)   => post('/api/account/me', body),
    update:        (body)   => patch('/api/account/me', body),
    subjects:      ()       => get('/api/account/me/subjects'),
    enrol:         (sid)    => post(`/api/account/me/subjects/${sid}`, {}),
  },
}
