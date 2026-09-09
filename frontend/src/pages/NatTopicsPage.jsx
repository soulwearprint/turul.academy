import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import BottomNav from '../components/BottomNav'
import { natTitle, lessonCountLabel } from '../lib/nat'

export default function NatTopicsPage() {
  const { session } = useAuth()
  const token = session?.access_token
  const [topics, setTopics] = useState([])
  const [subject, setSubject] = useState(null)
  const [grade, setGrade] = useState(null)
  const [loading, setLoading] = useState(true)
  const { t, lang } = useLang()
  const [searchParams] = useSearchParams()
  const subjectId = searchParams.get('subject')

  useEffect(() => {
    async function load() {
      const [tps, subjects] = await Promise.all([
        api.nat.topics(undefined, subjectId),
        api.curriculum.subjects(),
      ])
      setTopics(tps)
      setSubject(subjects.find(s => s.id === subjectId) ?? null)

      // Restore the last grade picked for this subject; else default to the
      // student's own grade — same convention as the legacy TopicsPage. Content
      // itself is never restricted by grade, this only picks the starting tab.
      if (subjectId) {
        const saved = sessionStorage.getItem(`ta_grade_${subjectId}`)
        if (saved !== null) {
          setGrade(saved === 'all' ? null : Number(saved))
        } else {
          try {
            const profile = await api.account.me(token)
            setGrade(profile.grade ?? null)
          } catch {
            setGrade(null)
          }
        }
      }
      setLoading(false)
    }
    load()
  }, [subjectId, token])

  function chooseGrade(g) {
    setGrade(g)
    if (subjectId) sessionStorage.setItem(`ta_grade_${subjectId}`, g === null ? 'all' : String(g))
  }

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>

  const allGrades = [...new Set(topics.map(tp => tp.grade))].sort((a, b) => a - b)
  const filteredTopics = grade ? topics.filter(tp => tp.grade === grade) : topics
  const byGrade = {}
  for (const tp of filteredTopics) (byGrade[tp.grade] ??= []).push(tp)
  const grades = Object.keys(byGrade).map(Number).sort((a, b) => a - b)
  // Subjects use name/name_hu, not title/title_hu (that's topics/lessons) — pick directly.
  const title = subject ? ((lang === 'en' ? subject.name : subject.name_hu) ?? subject.name_hu) : t('nat.default.title')

  return (
    <div className="pb-24">
      <PageHeader title={title} subtitle={t('nat.topics.subtitle', { n: topics.length })} backTo="/" />

      {/* Grade filter tabs — browsing, not gating: every grade is always reachable. */}
      {allGrades.length > 1 && (
        <div className="sticky top-[57px] bg-white border-b border-slate-100 z-30 overflow-x-auto">
          <div className="flex px-4 py-2 gap-2 min-w-max">
            <button
              onClick={() => chooseGrade(null)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                grade === null ? 'bg-turul-blue text-white' : 'text-slate-500 hover:bg-slate-100'
              }`}
            >
              {t('topics.all')}
            </button>
            {allGrades.map(g => (
              <button
                key={g}
                onClick={() => chooseGrade(g)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  grade === g ? 'bg-turul-blue text-white' : 'text-slate-500 hover:bg-slate-100'
                }`}
              >
                {g}{t('common.grade')}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="max-w-2xl mx-auto px-4 py-6">
        {grades.length === 0 ? (
          <div className="text-center text-slate-400 py-12">{t('topics.empty')}</div>
        ) : grades.map(g => (
          <section key={g} className="mb-6">
            <h2 className="font-bold text-slate-800 mb-3">{g}{t('common.grade')}</h2>
            <div className="flex flex-col gap-2">
              {byGrade[g].map(tp => (
                <Link key={tp.id} to={`/nat/topics/${tp.id}`}
                  className="flex items-center gap-3 bg-white rounded-xl border border-slate-100 shadow-sm px-4 py-3 hover:border-turul-blue/40 transition">
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-slate-800">{natTitle(tp, lang)}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{lessonCountLabel(t, tp.lesson_count ?? 0)}</div>
                  </div>
                  <span className="text-slate-300 text-xl shrink-0">›</span>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
      <BottomNav />
    </div>
  )
}
