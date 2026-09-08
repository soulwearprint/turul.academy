import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import BottomNav from '../components/BottomNav'
import { natTitle, lessonCountLabel } from '../lib/nat'

export default function NatTopicsPage() {
  const [topics, setTopics] = useState([])
  const [subject, setSubject] = useState(null)
  const [loading, setLoading] = useState(true)
  const { t, lang } = useLang()
  const [searchParams] = useSearchParams()
  const subjectId = searchParams.get('subject')

  useEffect(() => {
    Promise.all([
      api.nat.topics(undefined, subjectId),
      api.curriculum.subjects(),
    ]).then(([tps, subjects]) => {
      setTopics(tps)
      setSubject(subjects.find(s => s.id === subjectId) ?? null)
    }).finally(() => setLoading(false))
  }, [subjectId])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>

  const byGrade = {}
  for (const tp of topics) (byGrade[tp.grade] ??= []).push(tp)
  const grades = Object.keys(byGrade).map(Number).sort((a, b) => a - b)
  // Subjects use name/name_hu, not title/title_hu (that's topics/lessons) — pick directly.
  const title = subject ? ((lang === 'en' ? subject.name : subject.name_hu) ?? subject.name_hu) : t('nat.default.title')

  return (
    <div className="pb-24">
      <PageHeader title={title} subtitle={t('nat.topics.subtitle', { n: topics.length })} backTo="/" />

      <div className="max-w-2xl mx-auto px-4 py-6">
        {grades.map(g => (
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
