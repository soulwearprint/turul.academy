import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import BottomNav from '../components/BottomNav'
import TurulMascot from '../components/TurulMascot'
import { getTurulConfig, stageForGrade } from '../lib/turul'

function subjectIcon(code) {
  if (code.includes('HISTORY')) return '🏛️'
  if (code.includes('PHYSICS')) return '⚛️'
  if (code.includes('MATH')) return '📐'
  if (code.includes('BIOLOGY')) return '🧬'
  if (code.includes('CHEMISTRY')) return '🧪'
  return '📘'
}

export default function HomePage() {
  const { session, profile, signOut } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const [subjects, setSubjects] = useState([])
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(true)
  const config = getTurulConfig()

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
        <TurulMascot mood="idle" size={96} />
      </div>
    )
  }

  const xp = progress?.total_xp ?? 0
  const completed = progress?.completed_lessons ?? 0
  const streak = progress?.streak_days ?? 0
  const level = Math.floor(xp / 100) + 1
  const displayName = profile?.display_name ?? session?.user?.email?.split('@')[0] ?? 'Tanuló'
  const grade = profile?.grade ?? 7
  const stage = stageForGrade(grade)

  // Mascot mood reflects the student's momentum
  const mood = completed === 0 ? 'curious' : streak >= 3 ? 'celebrate' : 'happy'
  const statusKey = completed === 0 ? 'home.turul.new' : streak >= 3 ? 'home.turul.streak' : 'home.turul.back'

  const firstSubject = subjects[0]?.subject
  const continueTo = firstSubject ? `/subjects/${firstSubject.id}/topics` : '/subjects'

  return (
    <div className="pb-24">
      {/* Hero header */}
      <div className="hero-gradient px-5 pt-12 pb-16 rounded-b-3xl">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center justify-between mb-1">
            <p className="text-brand-100 text-sm">{t('home.greeting')}</p>
            <button onClick={signOut} className="text-brand-100/80 text-xs hover:text-white transition-colors">
              {t('home.signout')}
            </button>
          </div>
          <h1 className="text-2xl font-extrabold text-white font-display">{displayName} 👋</h1>

          <div className="mt-4 flex gap-2.5">
            <div className="chip"><span className="text-amber-300">🔥</span> {t('home.streak', { n: streak })}</div>
            <div className="chip"><span className="text-amber-300">⭐</span> {xp} XP</div>
            <div className="chip">Lv {level}</div>
          </div>
        </div>
      </div>

      <div className="px-4 -mt-9 max-w-lg mx-auto space-y-5">
        {/* Turul companion status card */}
        <Link to="/turul" className="card p-4 flex items-center gap-4 active:scale-[0.99] transition-transform animate-fade-up">
          <TurulMascot mood={mood} color={config.color} accessory={config.accessory} size={76} shadow={false} />
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-bold uppercase tracking-wide text-turul-blue">{stage.name[lang] ?? stage.name.hu}</p>
            <p className="text-sm text-slate-700 leading-snug mt-0.5">{t(statusKey)}</p>
          </div>
          <span className="text-slate-300 text-xl">›</span>
        </Link>

        {/* Continue learning — primary CTA */}
        <button
          onClick={() => navigate(continueTo)}
          className="w-full text-left rounded-2xl p-5 bg-turul-blue text-white shadow-glow-blue active:scale-[0.98] transition-transform"
        >
          <p className="text-brand-100 text-xs font-semibold uppercase tracking-wide">{t('home.continue.label')}</p>
          <p className="text-lg font-bold mt-1 font-display">
            {firstSubject ? firstSubject.name_hu : t('home.continue.start')}
          </p>
          <span className="inline-flex items-center gap-1.5 mt-3 bg-white/20 rounded-full px-4 py-1.5 text-sm font-semibold">
            {t('home.continue.cta')} →
          </span>
        </button>

        {/* My subjects */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-slate-800">{t('home.subjects.title')}</h2>
            <Link to="/subjects" className="text-turul-blue text-sm font-semibold">{t('home.subjects.add')}</Link>
          </div>

          {subjects.length === 0 ? (
            <div className="card p-6 text-center">
              <TurulMascot mood="curious" color={config.color} size={84} className="mx-auto" />
              <p className="text-slate-500 text-sm mt-2 mb-4">{t('home.no.subjects')}</p>
              <Link to="/subjects" className="btn-primary inline-flex">{t('home.choose.subject')}</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {subjects.map(({ subject }) => (
                <Link
                  key={subject.id}
                  to={`/subjects/${subject.id}/topics`}
                  className="card p-4 flex items-center gap-3 active:scale-[0.98] transition-transform"
                >
                  <div className="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center text-2xl">
                    {subjectIcon(subject.code)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-slate-900">{subject.name_hu}</div>
                    <div className="text-xs text-slate-500">{subject.grade_min}–{subject.grade_max}{t('subjects.grade.range')}</div>
                  </div>
                  <span className="text-slate-300 text-xl">›</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Daily tip */}
        <div className="rounded-2xl p-4 bg-amber-50 border border-amber-100">
          <p className="text-amber-900 text-sm font-semibold">{t('home.daily.tip.title')}</p>
          <p className="text-amber-800/90 text-sm mt-1 leading-relaxed">{t('home.daily.tip.body')}</p>
        </div>
      </div>

      <BottomNav />
    </div>
  )
}
