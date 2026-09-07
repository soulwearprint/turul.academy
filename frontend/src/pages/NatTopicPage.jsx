import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

// Status → card styling. Mirrors the lifecycle a Téma actually goes through:
// opened (in_progress) → every main tab viewed at least once (read) → quiz answered (completed).
const STATUS_STYLE = {
  in_progress: 'bg-amber-50 border-amber-200',
  read: 'bg-sky-50 border-sky-200',
  completed: 'bg-emerald-50 border-emerald-300',
}
const STATUS_BADGE = {
  in_progress: { label: 'Elkezdve', cls: 'bg-amber-100 text-amber-700' },
  read: { label: 'Elolvasva', cls: 'bg-sky-100 text-sky-700' },
  completed: { label: 'Kész ✓', cls: 'bg-emerald-100 text-emerald-700' },
}

export default function NatTopicPage() {
  const { topicId } = useParams()
  const { session } = useAuth()
  const token = session?.access_token
  const [topic, setTopic] = useState(null)
  const [lessonStatus, setLessonStatus] = useState({})
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      api.nat.topic(topicId),
      api.nat.progress(token).catch(() => null),
    ]).then(([t, prog]) => {
      setTopic(t)
      setLessonStatus(prog?.lesson_status ?? {})
    }).finally(() => setLoading(false))
  }, [topicId, token])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés…</div>
  if (!topic) return <div className="flex h-screen items-center justify-center text-slate-400">Nem található.</div>

  // Back to the topic list — keep the subject filter, otherwise this lands on the
  // unfiltered /nat list where every subject's topics interleave by grade.
  const backHref = topic.subject_id ? `/nat?subject=${topic.subject_id}` : '/nat'

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 pb-24">
      <div className="flex items-center gap-3 mb-1">
        <button onClick={() => navigate(backHref)} className="text-slate-400 hover:text-slate-600">←</button>
        <h1 className="text-2xl font-display font-bold text-slate-900">{topic.title_hu}</h1>
      </div>
      <p className="text-slate-500 text-sm mb-6 ml-7">{topic.grade}. évfolyam · {topic.temak.length} téma</p>

      <div className="flex flex-col gap-2">
        {topic.temak.map((l, i) => {
          const status = lessonStatus[l.id]
          const badge = status && STATUS_BADGE[status]
          return (
            <Link key={l.id} to={`/nat/lessons/${l.id}`}
              className={`flex items-center gap-3 rounded-xl border shadow-sm px-4 py-3 hover:border-turul-blue/40 transition ${STATUS_STYLE[status] ?? 'bg-white border-slate-100'}`}>
              <span className="w-7 h-7 shrink-0 rounded-full bg-turul-blue/10 text-turul-blue font-bold text-sm flex items-center justify-center">{i + 1}</span>
              <span className="font-semibold text-slate-800 flex-1">{l.title_hu}</span>
              {badge && (
                <span className={`shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded-full ${badge.cls}`}>{badge.label}</span>
              )}
            </Link>
          )
        })}
      </div>

      {topic.has_topic_quiz && (
        <Link to={`/nat/topics/${topic.id}/quiz`}
          className="mt-5 flex items-center justify-center gap-2 bg-turul-blue text-white font-semibold rounded-xl px-4 py-3.5 hover:bg-brand-700 transition">
          🎯 Témazáró kvíz
        </Link>
      )}
    </div>
  )
}
