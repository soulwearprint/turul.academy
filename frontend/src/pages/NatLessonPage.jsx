import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import { CardList, QuizRunner } from '../components/ContentCards'
import PageHeader from '../components/PageHeader'
import { natTitle } from '../lib/nat'

const MODE_EMOJI = { text: '📖', story: '🎭', visual: '🗺️', quiz: '🧠' }
const MAIN_MODES = ['text', 'story', 'visual', 'quiz']

// On-demand collapsible layer beyond the main tabs — a lesson has at most one of these.
const EXTRA_LAYERS = {
  world:      { key: 'nat.layer.world' },
  experiment: { key: 'nat.layer.experiment' },
}

export default function NatLessonPage() {
  const { lessonId } = useParams()
  const { session } = useAuth()
  const token = session?.access_token
  const { t, lang } = useLang()
  const [lesson, setLesson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState('text')
  const [showExtra, setShowExtra] = useState(false)
  const [viewedTabs, setViewedTabs] = useState(new Set())

  useEffect(() => {
    api.nat.lesson(lessonId).then(l => {
      setLesson(l)
      const firstMode = l.modes.find(m => MAIN_MODES.includes(m)) || 'text'
      setMode(firstMode)
      const seen = new Set([firstMode])
      setViewedTabs(seen)
      api.nat.setProgress(lessonId, { status: 'in_progress' }, token).catch(() => {})
      markReadIfComplete(l, seen)
    }).finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId, token])

  // "All cards read" = every non-quiz tab opened at least once (the quiz is a separate,
  // higher status — completing it is what actually moves a Téma to "completed").
  function markReadIfComplete(l, seen) {
    const readable = MAIN_MODES.filter(m => m !== 'quiz' && l.blocks[m])
    if (readable.length > 0 && readable.every(t => seen.has(t))) {
      api.nat.setProgress(lessonId, { status: 'read' }, token).catch(() => {})
    }
  }

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>
  if (!lesson) return <div className="flex h-screen items-center justify-center text-slate-400">{t('nat.not.found')}</div>

  const tabs = MAIN_MODES.filter(m => lesson.blocks[m])
  const extraMode = Object.keys(EXTRA_LAYERS).find(m => lesson.blocks[m])

  function openTab(m) {
    setMode(m)
    if (viewedTabs.has(m)) return
    const next = new Set(viewedTabs).add(m)
    setViewedTabs(next)
    markReadIfComplete(lesson, next)
  }

  return (
    <div className="pb-24">
      <PageHeader title={natTitle(lesson, lang)} backTo={-1} />

      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* Mode tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
          {tabs.map(m => (
            <button key={m} onClick={() => openTab(m)}
              className={`whitespace-nowrap px-3.5 py-2 rounded-full text-sm font-semibold transition ${
                mode === m ? 'bg-turul-blue text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
              {MODE_EMOJI[m]} {t(`mode.${m}`)}
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

        {/* On-demand extra layer (world for History, experiment for Physics) */}
        {extraMode && (
          <div className="mt-6">
            <button onClick={() => setShowExtra(s => !s)}
              className="w-full flex items-center justify-between bg-slate-900 text-white rounded-xl px-4 py-3 font-semibold">
              <span>{t(EXTRA_LAYERS[extraMode].key)}</span>
              <span className="text-white/60">{showExtra ? '▲' : '▼'}</span>
            </button>
            {showExtra && <div className="mt-3"><CardList mode={extraMode} cards={lesson.blocks[extraMode]} /></div>}
          </div>
        )}
      </div>
    </div>
  )
}
