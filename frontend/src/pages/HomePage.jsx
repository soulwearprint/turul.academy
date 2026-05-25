import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import BottomNav from '../components/BottomNav'
import ModeBadge from '../components/ModeBadge'

export default function HomePage() {
  const { session, profile, signOut } = useAuth()
  const navigate = useNavigate()
  const [subjects, setSubjects] = useState([])
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(true)

  const token = session?.access_token

  useEffect(() => {
    async function load() {
      try {
        const [enrolled, prog] = await Promise.all([
          api.account.subjects(token),
          api.progress.me(token),
        ])
        setSubjects(enrolled)
        setProgress(prog)
      } catch {
        // If no profile yet, redirect to onboarding
        navigate('/onboarding')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token, navigate])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-slate-400 animate-pulse">Betöltés...</div>
      </div>
    )
  }

  const xp = progress?.total_xp ?? 0
  const completed = progress?.completed_lessons ?? 0
  const displayName = profile?.display_name ?? session?.user?.email?.split('@')[0] ?? 'Tanuló'

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="bg-gradient-to-br from-turul-blue to-brand-700 px-5 pt-12 pb-8">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center justify-between mb-1">
            <p className="text-brand-200 text-sm">Üdv vissza,</p>
            <button onClick={signOut} className="text-brand-300 text-xs">Kilépés</button>
          </div>
          <h1 className="text-2xl font-bold text-white">{displayName} 👋</h1>

          {/* XP strip */}
          <div className="mt-4 flex gap-4">
            <div className="bg-white/20 rounded-xl px-4 py-2 flex-1 text-center">
              <div className="text-2xl font-bold text-white">{xp}</div>
              <div className="text-brand-200 text-xs">XP összesen</div>
            </div>
            <div className="bg-white/20 rounded-xl px-4 py-2 flex-1 text-center">
              <div className="text-2xl font-bold text-white">{completed}</div>
              <div className="text-brand-200 text-xs">Lecke kész</div>
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 mt-6 max-w-lg mx-auto space-y-6">
        {/* Enrolled subjects */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-slate-800">Tantárgyaim</h2>
            <Link to="/subjects" className="text-turul-blue text-sm font-medium">+ Hozzáadás</Link>
          </div>

          {subjects.length === 0 ? (
            <div className="card p-6 text-center">
              <div className="text-4xl mb-2">📚</div>
              <p className="text-slate-500 text-sm mb-4">Még nem iratkoztál be egy tantárgyra sem.</p>
              <Link to="/subjects" className="btn-primary inline-block">Tantárgy választás</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {subjects.map(({ subject }) => (
                <Link
                  key={subject.id}
                  to={`/subjects/${subject.id}/topics`}
                  className="card p-4 flex items-center gap-3 active:scale-[0.98] transition-transform"
                >
                  <div className="w-12 h-12 rounded-xl bg-turul-blue/10 flex items-center justify-center text-2xl">
                    {subject.code.includes('HISTORY') ? '🏛️' : '⚛️'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-slate-900">{subject.name_hu}</div>
                    <div className="text-xs text-slate-500">{subject.grade_min}–{subject.grade_max}. osztály</div>
                  </div>
                  <span className="text-slate-300">›</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Quick tip */}
        <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4">
          <p className="text-amber-800 text-sm font-medium">💡 Napi tipp</p>
          <p className="text-amber-700 text-sm mt-1">
            Próbáld ki a Történet módot — ugyanazt az anyagot élményszerű narratívában tanulhatod meg!
          </p>
        </div>
      </div>

      <BottomNav />
    </div>
  )
}
