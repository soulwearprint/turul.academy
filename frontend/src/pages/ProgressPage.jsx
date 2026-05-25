import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import BottomNav from '../components/BottomNav'

export default function ProgressPage() {
  const { session } = useAuth()
  const [progress, setProgress] = useState(null)
  const [subjects, setSubjects] = useState([])
  const [loading, setLoading] = useState(true)

  const token = session?.access_token

  useEffect(() => {
    async function load() {
      try {
        const [prog, enrolled] = await Promise.all([
          api.progress.me(token),
          api.account.subjects(token),
        ])
        setProgress(prog)
        setSubjects(enrolled)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [token])

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés...</div>
  }

  const xp = progress?.total_xp ?? 0
  const completed = progress?.completed_lessons ?? 0
  const badges = progress?.badges ?? []

  // XP level: every 100 XP = 1 level
  const level = Math.floor(xp / 100) + 1
  const levelProgress = xp % 100

  return (
    <div className="pb-24">
      <PageHeader title="Haladásom" />

      <div className="px-4 py-5 max-w-lg mx-auto space-y-5">
        {/* Level card */}
        <div className="card p-5">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-turul-blue flex items-center justify-center text-white text-2xl font-bold shrink-0">
              {level}
            </div>
            <div className="flex-1">
              <p className="font-bold text-slate-900">{level}. szint</p>
              <p className="text-sm text-slate-500">{xp} XP összesen</p>
              <div className="mt-2 bg-slate-100 rounded-full h-2">
                <div
                  className="h-full bg-turul-blue rounded-full transition-all"
                  style={{ width: `${levelProgress}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 mt-1">{levelProgress}/100 XP a következő szintig</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="card p-4 text-center">
            <div className="text-3xl font-bold text-turul-blue">{completed}</div>
            <div className="text-sm text-slate-500 mt-1">Kész lecke</div>
          </div>
          <div className="card p-4 text-center">
            <div className="text-3xl font-bold text-turul-gold">{badges.length}</div>
            <div className="text-sm text-slate-500 mt-1">Kitűző</div>
          </div>
        </div>

        {/* Per-subject progress */}
        {subjects.length > 0 && (
          <section>
            <h2 className="font-bold text-slate-800 mb-3">Tantárgyak szerint</h2>
            <div className="space-y-3">
              {subjects.map(({ subject }) => (
                <SubjectProgress key={subject.id} subject={subject} token={token} />
              ))}
            </div>
          </section>
        )}

        {/* Badges */}
        {badges.length > 0 && (
          <section>
            <h2 className="font-bold text-slate-800 mb-3">Kitűzők</h2>
            <div className="flex flex-wrap gap-2">
              {badges.map(b => (
                <div key={b.id} className="card px-3 py-2 flex items-center gap-2">
                  <span className="text-xl">{b.badge?.icon ?? '🏅'}</span>
                  <span className="text-sm font-medium">{b.badge?.name ?? b.badge_id}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>

      <BottomNav />
    </div>
  )
}

function SubjectProgress({ subject, token }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    api.progress.subject(subject.id, token).then(setData).catch(() => {})
  }, [subject.id, token])

  const pct = data?.completion_percent ?? 0

  return (
    <div className="card p-4">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-xl">{subject.code.includes('HISTORY') ? '🏛️' : '⚛️'}</span>
        <span className="font-semibold text-sm">{subject.name_hu}</span>
        <span className="ml-auto text-sm font-bold text-turul-blue">{pct}%</span>
      </div>
      <div className="bg-slate-100 rounded-full h-2">
        <div
          className="h-full bg-turul-blue rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
