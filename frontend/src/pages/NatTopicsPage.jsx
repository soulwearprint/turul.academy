import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import BottomNav from '../components/BottomNav'

export default function NatTopicsPage() {
  const [topics, setTopics] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.nat.topics().then(setTopics).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés…</div>

  const byGrade = {}
  for (const t of topics) (byGrade[t.grade] ??= []).push(t)
  const grades = Object.keys(byGrade).map(Number).sort((a, b) => a - b)

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 pb-24">
      <div className="flex items-center gap-3 mb-1">
        <button onClick={() => navigate('/')} className="text-slate-400 hover:text-slate-600">←</button>
        <h1 className="text-2xl font-display font-bold text-slate-900">Történelem – NAT tananyag</h1>
      </div>
      <p className="text-slate-500 text-sm mb-6 ml-7">Előnézet · {topics.length} témakör a 2020-as NAT szerint</p>

      {grades.map(g => (
        <section key={g} className="mb-6">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">{g}. évfolyam</h2>
          <div className="flex flex-col gap-2">
            {byGrade[g].map(t => (
              <Link key={t.id} to={`/nat/topics/${t.id}`}
                className="block bg-white rounded-xl border border-slate-100 shadow-sm px-4 py-3 hover:border-turul-blue/40 transition">
                <span className="font-semibold text-slate-800">{t.title_hu}</span>
              </Link>
            ))}
          </div>
        </section>
      ))}
      <BottomNav />
    </div>
  )
}
