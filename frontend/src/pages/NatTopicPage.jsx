import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export default function NatTopicPage() {
  const { topicId } = useParams()
  const [topic, setTopic] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.nat.topic(topicId).then(setTopic).finally(() => setLoading(false))
  }, [topicId])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés…</div>
  if (!topic) return <div className="flex h-screen items-center justify-center text-slate-400">Nem található.</div>

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 pb-24">
      <div className="flex items-center gap-3 mb-1">
        <button onClick={() => navigate('/nat')} className="text-slate-400 hover:text-slate-600">←</button>
        <h1 className="text-2xl font-display font-bold text-slate-900">{topic.title_hu}</h1>
      </div>
      <p className="text-slate-500 text-sm mb-6 ml-7">{topic.grade}. évfolyam · {topic.temak.length} téma</p>

      <div className="flex flex-col gap-2">
        {topic.temak.map((l, i) => (
          <Link key={l.id} to={`/nat/lessons/${l.id}`}
            className="flex items-center gap-3 bg-white rounded-xl border border-slate-100 shadow-sm px-4 py-3 hover:border-turul-blue/40 transition">
            <span className="w-7 h-7 shrink-0 rounded-full bg-turul-blue/10 text-turul-blue font-bold text-sm flex items-center justify-center">{i + 1}</span>
            <span className="font-semibold text-slate-800">{l.title_hu}</span>
          </Link>
        ))}
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
