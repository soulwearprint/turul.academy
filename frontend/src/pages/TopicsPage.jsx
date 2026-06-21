import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import BottomNav from '../components/BottomNav'
import ModeBadge from '../components/ModeBadge'

function groupByGrade(topics) {
  const groups = {}
  for (const t of topics) {
    if (!groups[t.grade]) groups[t.grade] = []
    groups[t.grade].push(t)
  }
  return groups
}

export default function TopicsPage() {
  const { subjectId } = useParams()
  const { session } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const [subject, setSubject] = useState(null)
  const [topics, setTopics] = useState([])
  const [grade, setGrade] = useState(null)
  const [loading, setLoading] = useState(true)

  const token = session?.access_token

  useEffect(() => {
    async function load() {
      try {
        const [subjects, allTopics] = await Promise.all([
          api.curriculum.subjects(),
          api.curriculum.topics(subjectId),
        ])
        const s = subjects.find(s => s.id === subjectId)
        setSubject(s)
        setTopics(allTopics)
        // Restore the last grade the user picked for this subject; else default to profile grade
        const saved = sessionStorage.getItem(`ta_grade_${subjectId}`)
        if (saved !== null) {
          setGrade(saved === 'all' ? null : Number(saved))
        } else if (session?.user) {
          try {
            const profile = await api.account.me(token)
            setGrade(profile.grade ?? s?.grade_min ?? allTopics[0]?.grade)
          } catch {
            setGrade(s?.grade_min ?? allTopics[0]?.grade)
          }
        }
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [subjectId, token])

  function chooseGrade(g) {
    setGrade(g)
    sessionStorage.setItem(`ta_grade_${subjectId}`, g === null ? 'all' : String(g))
  }

  const grades = [...new Set(topics.map(t => t.grade))].sort((a, b) => a - b)
  const filteredTopics = grade ? topics.filter(t => t.grade === grade) : topics

  return (
    <div className="pb-24">
      <PageHeader
        title={(lang === 'en' ? subject?.name : subject?.name_hu) ?? subject?.name_hu ?? 'Témakörök'}
        subtitle={`${topics.length} ${t('topics.count')}`}
        backTo="/"
      />

      {/* Grade filter tabs */}
      {grades.length > 1 && (
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
            {grades.map(g => (
              <button
                key={g}
                onClick={() => chooseGrade(g)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  grade === g ? 'bg-turul-blue text-white' : 'text-slate-500 hover:bg-slate-100'
                }`}
              >
                {g}{t('topics.grade')}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="px-4 py-4 max-w-lg mx-auto space-y-2">
        {loading ? (
          <div className="text-center text-slate-400 py-12">{t('common.loading')}</div>
        ) : filteredTopics.length === 0 ? (
          <div className="text-center text-slate-400 py-12">{t('topics.empty')}</div>
        ) : filteredTopics.map(topic => (
          <button
            key={topic.id}
            onClick={() => navigate(`/subjects/${subjectId}/topics/${topic.id}`)}
            className="card w-full p-4 text-left active:scale-[0.98] transition-transform block"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                <span className="text-xs font-mono text-slate-400 bg-slate-50 rounded px-1.5 py-0.5">
                  {topic.nat_id}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-slate-900 text-sm">
                  {(lang === 'en' ? topic.title : topic.title_hu) ?? topic.title_hu}
                </div>

                {/* Show available lesson modes */}
                {topic.lessons && topic.lessons.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {topic.lessons.filter(l => l.is_active).map(l => (
                      <ModeBadge key={l.id} mode={l.mode} />
                    ))}
                  </div>
                )}
              </div>
              <span className="text-slate-300 shrink-0">›</span>
            </div>
          </button>
        ))}
      </div>

      <BottomNav />
    </div>
  )
}
