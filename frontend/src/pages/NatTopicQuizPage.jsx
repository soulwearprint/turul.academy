import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { CardList } from '../components/ContentCards'

export default function NatTopicQuizPage() {
  const { topicId } = useParams()
  const [cards, setCards] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.nat.topicQuiz(topicId).then(d => setCards(d.cards)).finally(() => setLoading(false))
  }, [topicId])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés…</div>

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 pb-24">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate(-1)} className="text-slate-400 hover:text-slate-600">←</button>
        <h1 className="text-xl font-display font-bold text-slate-900">🎯 Témazáró kvíz</h1>
      </div>
      <CardList mode="quiz" cards={cards} />
    </div>
  )
}
