import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import { natTitle, lessonCountLabel } from '../lib/nat'

// Status → card styling. Mirrors the lifecycle a Téma actually goes through:
// opened (in_progress) → every main tab viewed at least once (read) → quiz answered (completed).
const STATUS_STYLE = {
  in_progress: 'bg-amber-50 border-amber-200',
  read: 'bg-sky-50 border-sky-200',
  completed: 'bg-emerald-50 border-emerald-300',
}
const STATUS_KEY = {
  in_progress: 'nat.status.started',
  read: 'nat.status.read',
  completed: 'nat.status.completed',
}
const STATUS_BADGE_CLS = {
  in_progress: 'bg-amber-100 text-amber-700',
  read: 'bg-sky-100 text-sky-700',
  completed: 'bg-emerald-100 text-emerald-700',
}

export default function NatTopicPage() {
  const { topicId } = useParams()
  const { session } = useAuth()
  const token = session?.access_token
  const { t, lang } = useLang()
  const [topic, setTopic] = useState(null)
  const [lessonStatus, setLessonStatus] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.nat.topic(topicId),
      api.nat.progress(token).catch(() => null),
    ]).then(([tp, prog]) => {
      setTopic(tp)
      setLessonStatus(prog?.lesson_status ?? {})
    }).finally(() => setLoading(false))
  }, [topicId, token])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>
  if (!topic) return <div className="flex h-screen items-center justify-center text-slate-400">{t('nat.not.found')}</div>

  // Back to the topic list — keep the subject filter, otherwise this lands on the
  // unfiltered /nat list where every subject's topics interleave by grade.
  const backHref = topic.subject_id ? `/nat?subject=${topic.subject_id}` : '/nat'

  return (
    <div className="pb-24">
      <PageHeader
        title={natTitle(topic, lang)}
        subtitle={`${topic.grade}${t('common.grade')} · ${lessonCountLabel(t, topic.temak.length)}`}
        backTo={backHref}
      />

      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex flex-col gap-2">
          {topic.temak.map((l, i) => {
            const status = lessonStatus[l.id]
            return (
              <Link key={l.id} to={`/nat/lessons/${l.id}`}
                className={`flex items-center gap-3 rounded-xl border shadow-sm px-4 py-3 hover:border-turul-blue/40 transition ${STATUS_STYLE[status] ?? 'bg-white border-slate-100'}`}>
                <span className="w-7 h-7 shrink-0 rounded-full bg-turul-blue/10 text-turul-blue font-bold text-sm flex items-center justify-center">{i + 1}</span>
                <span className="font-semibold text-slate-800 flex-1">{natTitle(l, lang)}</span>
                {status && (
                  <span className={`shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded-full ${STATUS_BADGE_CLS[status]}`}>{t(STATUS_KEY[status])}</span>
                )}
              </Link>
            )
          })}
        </div>

        {topic.has_topic_quiz && (
          <Link to={`/nat/topics/${topic.id}/quiz`}
            className="mt-5 flex items-center justify-center gap-2 bg-turul-blue text-white font-semibold rounded-xl px-4 py-3.5 hover:bg-brand-700 transition">
            {t('nat.topic.quiz')}
          </Link>
        )}
      </div>
    </div>
  )
}
