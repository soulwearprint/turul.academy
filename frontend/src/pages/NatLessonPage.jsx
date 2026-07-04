import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import { CardList, QuizRunner } from '../components/ContentCards'

const MODE_LABELS = { text: '📖 Szöveg', story: '🎭 Történet', visual: '🗺️ Vizuális', quiz: '🧠 Kvíz' }
const MAIN_MODES = ['text', 'story', 'visual', 'quiz']

export default function NatLessonPage() {
  const { lessonId } = useParams()
  const { session } = useAuth()
  const token = session?.access_token
  const [lesson, setLesson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState('text')
  const [showWorld, setShowWorld] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.nat.lesson(lessonId).then(l => {
      setLesson(l)
      setMode(l.modes.find(m => MAIN_MODES.includes(m)) || 'text')
      api.nat.setProgress(lessonId, { status: 'in_progress' }, token).catch(() => {})
    }).finally(() => setLoading(false))
  }, [lessonId, token])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés…</div>
  if (!lesson) return <div className="flex h-screen items-center justify-center text-slate-400">Nem található.</div>

  const tabs = MAIN_MODES.filter(m => lesson.blocks[m])
  const hasWorld = !!lesson.blocks.world

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 pb-24">
      <div className="flex items-center gap-3 mb-4">
        <button onClick={() => navigate(-1)} className="text-slate-400 hover:text-slate-600">←</button>
        <h1 className="text-xl font-display font-bold text-slate-900">{lesson.title_hu}</h1>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
        {tabs.map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={`whitespace-nowrap px-3.5 py-2 rounded-full text-sm font-semibold transition ${
              mode === m ? 'bg-turul-blue text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      {mode === 'quiz' ? (
        <QuizRunner
          cards={lesson.blocks.quiz}
          onSubmit={(answers) => api.nat.submitQuiz(
            { topic_id: lesson.topic_id, lesson_id: lessonId, scope: 'lesson', answers }, token)}
        />
      ) : (
        <CardList mode={mode} cards={lesson.blocks[mode]} />
      )}

      {/* Világ ekkor — on-demand global layer */}
      {hasWorld && (
        <div className="mt-6">
          <button onClick={() => setShowWorld(s => !s)}
            className="w-full flex items-center justify-between bg-slate-900 text-white rounded-xl px-4 py-3 font-semibold">
            <span>🌍 Világ ekkor</span>
            <span className="text-white/60">{showWorld ? '▲' : '▼'}</span>
          </button>
          {showWorld && <div className="mt-3"><CardList mode="world" cards={lesson.blocks.world} /></div>}
        </div>
      )}
    </div>
  )
}
