import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'

export default function QuizPage() {
  const { lessonId } = useParams()
  const { session } = useAuth()
  const { t } = useLang()
  const navigate = useNavigate()
  const [lesson, setLesson] = useState(null)
  const [cards, setCards] = useState([])
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)

  const token = session?.access_token

  useEffect(() => {
    async function load() {
      const l = await api.lessons.get(lessonId, token)
      setLesson(l)
      setCards(l.content ?? [])
      setLoading(false)
    }
    load()
  }, [lessonId, token])

  function selectAnswer(optionLetter) {
    setAnswers(prev => ({ ...prev, [index]: optionLetter }))
  }

  async function submit() {
    const answersPayload = cards.map((card, i) => ({
      question_index: i,
      question: card.question,
      chosen: answers[i] ?? null,
      correct: card.correct,
    }))
    const correct = answersPayload.filter(a => a.chosen === a.correct).length
    const score = Math.round((correct / cards.length) * 100)
    await api.lessons.updateProgress(lessonId, { status: 'completed', mode_used: 'quiz' }, token)
    setResult({ correct, total: cards.length, score, answers: answersPayload })
    setSubmitted(true)
  }

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>

  // Results screen
  if (submitted && result) {
    const emoji = result.score === 100 ? '🏆' : result.score >= 75 ? '🎉' : result.score >= 50 ? '👍' : '📖'
    return (
      <div className="min-h-screen bg-slate-50 pb-12">
        <div className="bg-gradient-to-br from-turul-blue to-brand-700 px-5 pt-16 pb-10 text-center">
          <div className="text-6xl mb-3">{emoji}</div>
          <div className="text-5xl font-bold text-white mb-1">{result.score}%</div>
          <p className="text-brand-200">{result.correct}{t('quiz.results.correct', { total: result.total })}</p>
        </div>

        <div className="px-4 py-5 max-w-lg mx-auto space-y-4">
          {result.answers.map((a, i) => {
            const isCorrect = a.chosen === a.correct
            const card = cards[i]
            return (
              <div key={i} className={`rounded-2xl border-2 p-4 ${
                isCorrect ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
              }`}>
                <p className="font-semibold text-slate-800 text-sm mb-2">
                  {isCorrect ? '✅' : '❌'} {a.question}
                </p>
                {!isCorrect && (
                  <p className="text-sm text-red-700 mb-1">
                    {t('quiz.your.answer')} <strong>{a.chosen ?? t('quiz.no.answer')}</strong>
                    {' · '}
                    {t('quiz.right.answer')} <strong>{a.correct}</strong>
                  </p>
                )}
                {card.explanation && (
                  <p className="text-sm text-slate-600 italic mt-2 border-t border-slate-200 pt-2">
                    {card.explanation}
                  </p>
                )}
              </div>
            )
          })}

          <button onClick={() => navigate(-1)} className="btn-primary w-full text-center mt-4">
            {t('quiz.results.back')}
          </button>
        </div>
      </div>
    )
  }

  // Quiz player
  const card = cards[index]
  const chosen = answers[index]
  const allAnswered = cards.length > 0 && cards.every((_, i) => answers[i] !== undefined)

  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      <div className="bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="w-9 h-9 flex items-center justify-center rounded-xl hover:bg-slate-100 text-slate-500"
        >
          {t('common.close')}
        </button>
        <div className="flex-1 bg-slate-100 rounded-full h-2">
          <div
            className="h-full bg-turul-green rounded-full transition-all duration-500"
            style={{ width: `${Object.keys(answers).length / Math.max(cards.length, 1) * 100}%` }}
          />
        </div>
        <span className="text-sm text-slate-500 font-medium">{index + 1}/{cards.length}</span>
      </div>

      <div className="flex-1 px-4 py-6 max-w-lg mx-auto w-full">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 mb-5">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
            {index + 1}{t('quiz.question.label')}
          </p>
          <p className="font-bold text-slate-900 text-lg leading-snug">{card?.question}</p>
        </div>

        <div className="space-y-3">
          {(card?.options ?? []).map(opt => {
            const letter = opt.charAt(0)
            const isChosen = chosen === letter
            return (
              <button
                key={letter}
                onClick={() => selectAnswer(letter)}
                className={`w-full text-left px-4 py-4 rounded-xl border-2 font-medium text-sm transition-all ${
                  isChosen
                    ? 'border-turul-blue bg-blue-50 text-turul-blue'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                }`}
              >
                {opt}
              </button>
            )
          })}
        </div>
      </div>

      <div className="px-4 pb-8 pt-2 max-w-lg mx-auto w-full space-y-2">
        <div className="flex gap-2">
          {index > 0 && (
            <button onClick={() => setIndex(i => i - 1)} className="btn-secondary h-12 px-5">
              {t('quiz.back')}
            </button>
          )}
          {index < cards.length - 1 ? (
            <button
              onClick={() => setIndex(i => i + 1)}
              disabled={!chosen}
              className="btn-primary flex-1 h-12"
            >
              {t('quiz.next')}
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={!allAnswered}
              className="btn-primary flex-1 h-12"
            >
              {t('quiz.submit')}
            </button>
          )}
        </div>

        <div className="flex justify-center gap-1.5 pt-1">
          {cards.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              className={`w-2 h-2 rounded-full transition-all ${
                i === index ? 'bg-turul-blue w-4' : answers[i] ? 'bg-turul-green' : 'bg-slate-300'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
