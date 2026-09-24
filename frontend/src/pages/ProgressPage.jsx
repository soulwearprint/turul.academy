import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import { BADGES, fmtDuration } from '../lib/badges'
import { subjectIcon } from '../lib/nat'
import PageHeader from '../components/PageHeader'
import BottomNav from '../components/BottomNav'
import StudyHeatmap from '../components/StudyHeatmap'
import TopicStats from '../components/TopicStats'

export default function ProgressPage() {
  const { session } = useAuth()
  const { t, lang } = useLang()
  const [progress, setProgress] = useState(null)
  const [subjects, setSubjects] = useState([])
  const [stats, setStats] = useState(null)
  const [activity, setActivity] = useState(null)
  const [review, setReview] = useState(null)
  const [earned, setEarned] = useState([])
  const [loading, setLoading] = useState(true)

  const token = session?.access_token

  const load = useCallback(async () => {
    const soft = (p) => p.catch(() => null)
    try {
      // Badges first: that call also awards anything newly qualified, so the
      // summary below counts it.
      const badges = await soft(api.progress.badges(token))
      const [prog, enrolled, st, act, rev] = await Promise.all([
        api.progress.me(token),
        soft(api.account.subjects(token)),
        soft(api.nat.stats(token)),
        soft(api.progress.activity(token)),
        soft(api.nat.review(token)),
      ])
      setEarned(badges ?? prog?.badges ?? [])
      setProgress(prog)
      setSubjects(enrolled ?? [])
      setStats(st)
      setActivity(act)
      setReview(rev)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { load() }, [load])

  async function resetLesson(lessonId) {
    await api.nat.resetLesson(lessonId, token)
    await load()
  }

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>
  }

  const xp = progress?.total_xp ?? 0
  const completed = progress?.completed_lessons ?? 0
  const earnedTypes = new Set(earned.map(b => b.badge_type))

  // XP level: every 100 XP = 1 level
  const level = Math.floor(xp / 100) + 1
  const levelProgress = xp % 100

  return (
    <div className="pb-24">
      <PageHeader title={t('progress.title')} />

      <div className="px-4 py-5 max-w-lg mx-auto space-y-5">
        {/* Level card */}
        <div className="card p-5">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-turul-blue flex items-center justify-center text-white text-2xl font-bold shrink-0">
              {level}
            </div>
            <div className="flex-1">
              <p className="font-bold text-slate-900">{level}{t('progress.level')}</p>
              <p className="text-sm text-slate-500">{xp} {t('progress.xp.total')}</p>
              <div className="mt-2 bg-slate-100 rounded-full h-2">
                <div
                  className="h-full bg-turul-blue rounded-full transition-all"
                  style={{ width: `${levelProgress}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 mt-1">{levelProgress}{t('progress.xp.to.next')}</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <StatTile value={completed} label={t('progress.lessons')} cls="text-turul-blue" />
          <StatTile value={fmtDuration(activity?.total_seconds ?? stats?.totals?.seconds ?? 0, lang)} label={t('progress.time')} cls="text-brand-700" />
          <StatTile value={`🔥 ${progress?.streak_days ?? 0}`} label={t('progress.streak')} cls="text-orange-500" />
          <StatTile value={`${earnedTypes.size}/${BADGES.length}`} label={t('progress.badges')} cls="text-turul-amber" />
        </div>

        {activity && <StudyHeatmap data={activity} t={t} lang={lang} />}

        {/* Questions you keep missing */}
        {review && (stats?.totals?.quizzes ?? 0) > 0 && (
          <div className="card p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <h2 className="font-bold text-slate-800">🔁 {t('review.title')}</h2>
                <p className="text-sm text-slate-500 mt-0.5">
                  {review.count > 0 ? t('review.teaser', { n: review.count }) : t('review.teaser.none')}
                </p>
              </div>
              {review.count > 0 && (
                <Link to="/review" className="shrink-0 px-3.5 py-2 rounded-xl bg-turul-blue text-white text-sm font-semibold">
                  {t('review.practice')}
                </Link>
              )}
            </div>
            {review.items.slice(0, 2).map(q => (
              <div key={`${q.scope}-${q.lesson_id ?? q.topic_id}-${q.index}`} className="mt-3 pt-3 border-t border-slate-100">
                <p className="text-sm text-slate-700 line-clamp-2">{q.question}</p>
                <p className="text-[11px] text-red-500 font-semibold mt-1">{t('review.missed', { n: q.misses })}</p>
              </div>
            ))}
          </div>
        )}

        {/* Per-topic time + quiz retention */}
        {stats && (stats.topics.length > 0
          ? <TopicStats topics={stats.topics} t={t} lang={lang} onResetLesson={resetLesson} />
          : (
            <section>
              <h2 className="font-bold text-slate-800 mb-2">{t('progress.topics.title')}</h2>
              <p className="card p-4 text-sm text-slate-500">{t('progress.topics.empty')}</p>
            </section>
          ))}

        {/* Badges — earned in colour, the rest greyed out with how to earn them */}
        <section>
          <h2 className="font-bold text-slate-800 mb-3">{t('progress.badges.title')}</h2>
          <div className="grid grid-cols-3 gap-2.5">
            {BADGES.map(b => {
              const has = earnedTypes.has(b.type)
              return (
                <div key={b.type} className={`card p-3 text-center ${has ? '' : 'bg-slate-50 shadow-none'}`}>
                  <div className={`text-3xl ${has ? '' : 'grayscale opacity-30'}`}>{b.icon}</div>
                  <p className={`text-xs font-bold mt-1.5 leading-tight ${has ? 'text-slate-800' : 'text-slate-400'}`}>
                    {t(`badge.${b.type}.name`)}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1 leading-snug">{t(`badge.${b.type}.desc`)}</p>
                </div>
              )
            })}
          </div>
        </section>

        {/* Per-subject progress */}
        {subjects.length > 0 && (
          <section>
            <h2 className="font-bold text-slate-800 mb-3">{t('progress.subjects.title')}</h2>
            <div className="space-y-3">
              {subjects.map(({ subject }) => (
                <SubjectProgress key={subject.id} subject={subject} token={token} lang={lang} />
              ))}
            </div>
          </section>
        )}
      </div>

      <BottomNav />
    </div>
  )
}

function StatTile({ value, label, cls }) {
  return (
    <div className="card p-4 text-center">
      <div className={`text-2xl font-bold ${cls}`}>{value}</div>
      <div className="text-sm text-slate-500 mt-1">{label}</div>
    </div>
  )
}

function SubjectProgress({ subject, token, lang }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    api.progress.subject(subject.id, token).then(setData).catch(() => {})
  }, [subject.id, token])

  const pct = data?.completion_pct ?? 0
  const name = (lang === 'en' ? subject.name : subject.name_hu) ?? subject.name_hu

  return (
    <div className="card p-4">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-xl">{subjectIcon(subject.code)}</span>
        <span className="font-semibold text-sm">{name}</span>
        <span className="ml-auto text-sm font-bold text-turul-blue">
          {data?.lessons_total ? <span className="text-xs font-medium text-slate-400 mr-2">{data.lessons_done}/{data.lessons_total}</span> : null}
          {pct}%
        </span>
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
