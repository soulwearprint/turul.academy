import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import PageHeader from '../components/PageHeader'
import ModeBadge from '../components/ModeBadge'
import BottomNav from '../components/BottomNav'

const MODE_ORDER = ['text', 'story', 'visual', 'quiz']

export default function TopicDetailPage() {
  const { subjectId, topicId } = useParams()
  const { session } = useAuth()
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const [topic, setTopic] = useState(null)
  const [lessons, setLessons] = useState([])
  const [completedIds, setCompletedIds] = useState(new Set())
  const [loading, setLoading] = useState(true)

  const token = session?.access_token

  useEffect(() => {
    async function load() {
      try {
        const [tp, l, prog] = await Promise.all([
          api.curriculum.topic(topicId),
          api.lessons.forTopic(topicId),
          api.progress.me(token).catch(() => null),
        ])
        setTopic(tp)
        setLessons(l)
        const done = (prog?.completed_lessons ?? [])
          .filter(c => c.topic_id === topicId)
          .map(c => c.lesson_id)
        setCompletedIds(new Set(done))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [topicId, token])

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>
  }

  const activeByMode = Object.fromEntries(lessons.map(l => [l.mode, l]))

  return (
    <div className="pb-24">
      <PageHeader
        title={(lang === 'en' ? topic?.title : topic?.title_hu) ?? topic?.title_hu ?? ''}
        subtitle={topic?.nat_id}
        backTo={`/subjects/${subjectId}/topics`}
      />

      <div className="px-4 py-5 max-w-lg mx-auto">
        {/* Topic info */}
        <div className="card p-4 mb-5">
          <div className="flex flex-wrap gap-1.5">
            <span className="text-xs bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">
              {topic?.grade}{t('common.grade')}
            </span>
            <span className="text-xs bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">
              {topic?.semester}{t('topic.semester')}
            </span>
          </div>
        </div>

        {/* Mode cards */}
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold text-slate-800">{t('topic.modes.title')}</h2>
          {lessons.length > 0 && (
            <span className="text-xs font-semibold text-slate-500">
              {t('topic.progress', { done: lessons.filter(l => completedIds.has(l.id)).length, total: lessons.length })}
            </span>
          )}
        </div>

        {lessons.length === 0 ? (
          <div className="card p-8 text-center text-slate-400">
            <div className="text-4xl mb-2">🚧</div>
            <p>{t('topic.no.lessons')}</p>
            <p className="text-sm mt-1">{t('topic.coming.soon')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {MODE_ORDER.map(mode => {
              const lesson = activeByMode[mode]
              if (!lesson) return null
              const done = completedIds.has(lesson.id)
              return (
                <button
                  key={mode}
                  onClick={() => navigate(
                    mode === 'quiz'
                      ? `/lessons/${lesson.id}/quiz`
                      : `/lessons/${lesson.id}`
                  )}
                  className={`card w-full p-4 text-left active:scale-[0.98] transition-transform ${
                    done ? 'border-turul-green/40 bg-green-50/40' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <ModeBadge mode={mode} size="lg" />
                        {done && (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-turul-green bg-green-100 rounded-full px-2 py-0.5">
                            ✓ {t('topic.done')}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-500 mt-1.5">{t(`mode.${mode}.desc`)}</p>
                      {lesson.reading_time_minutes && (
                        <p className="text-xs text-slate-400 mt-1">
                          ⏱ {t('topic.minutes', { n: lesson.reading_time_minutes })}
                        </p>
                      )}
                    </div>
                    <span className={`text-xl ${done ? 'text-turul-green' : 'text-slate-300'}`}>›</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      <BottomNav />
    </div>
  )
}
