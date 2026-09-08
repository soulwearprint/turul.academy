import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import { QuizRunner } from '../components/ContentCards'
import PageHeader from '../components/PageHeader'

export default function NatTopicQuizPage() {
  const { topicId } = useParams()
  const { session } = useAuth()
  const token = session?.access_token
  const { t } = useLang()
  const [cards, setCards] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.nat.topicQuiz(topicId).then(d => setCards(d.cards)).finally(() => setLoading(false))
  }, [topicId])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>

  return (
    <div className="pb-24">
      <PageHeader title={t('nat.topic.quiz')} backTo={-1} />
      <div className="max-w-2xl mx-auto px-4 py-6">
        <QuizRunner
          cards={cards}
          onSubmit={(answers) => api.nat.submitQuiz({ topic_id: topicId, scope: 'topic', answers }, token)}
        />
      </div>
    </div>
  )
}
