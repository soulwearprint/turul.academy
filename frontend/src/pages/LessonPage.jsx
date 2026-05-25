import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import ModeBadge from '../components/ModeBadge'

// ─── Card renderers ───────────────────────────────────────────

function TextCard({ card }) {
  return (
    <div className="h-full flex flex-col justify-center px-6 py-8 gap-5">
      <h2 className="text-2xl font-bold text-slate-900 leading-snug">{card.heading}</h2>
      <p className="text-slate-700 leading-relaxed text-base">{card.body}</p>
      {card.key_term && (
        <div className="bg-turul-blue/10 border border-turul-blue/20 rounded-xl px-4 py-3">
          <span className="text-xs font-semibold text-turul-blue uppercase tracking-wide">Kulcsfogalom</span>
          <p className="font-bold text-turul-blue mt-0.5">{card.key_term}</p>
        </div>
      )}
    </div>
  )
}

const MOOD_COLORS = {
  tense:    'from-red-900 to-red-700',
  dramatic: 'from-purple-900 to-purple-700',
  curious:  'from-amber-800 to-amber-600',
  hopeful:  'from-emerald-800 to-emerald-600',
  solemn:   'from-slate-800 to-slate-600',
}

function StoryCard({ card }) {
  const gradient = MOOD_COLORS[card.mood] ?? 'from-slate-800 to-slate-600'
  return (
    <div className={`h-full flex flex-col justify-end bg-gradient-to-b ${gradient} px-6 py-10 gap-4`}>
      <span className="text-white/60 text-xs font-semibold uppercase tracking-widest">
        {card.mood ? `— ${card.mood}` : ''}
      </span>
      <h2 className="text-2xl font-bold text-white leading-snug">{card.heading}</h2>
      <p className="text-white/85 leading-relaxed text-base">{card.body}</p>
    </div>
  )
}

const VISUAL_ICONS = {
  timeline: '📅',
  map:      '🗺️',
  diagram:  '📊',
  portrait: '🖼️',
  chart:    '📈',
}

function VisualCard({ card }) {
  return (
    <div className="h-full flex flex-col px-6 py-8 gap-5">
      <div className="bg-slate-100 rounded-2xl flex-1 flex flex-col items-center justify-center gap-3 min-h-[180px]">
        <span className="text-5xl">{VISUAL_ICONS[card.visual_type] ?? '🖼️'}</span>
        <span className="text-slate-500 text-sm font-medium capitalize">{card.visual_type}</span>
      </div>
      <h2 className="text-xl font-bold text-slate-900">{card.heading}</h2>
      <p className="text-slate-700 leading-relaxed text-sm">{card.description}</p>
      {card.caption && (
        <p className="text-xs text-slate-400 italic border-t border-slate-100 pt-3">{card.caption}</p>
      )}
    </div>
  )
}

// ─── Lesson Player ────────────────────────────────────────────

export default function LessonPage() {
  const { lessonId } = useParams()
  const { session } = useAuth()
  const navigate = useNavigate()
  const [lesson, setLesson] = useState(null)
  const [cards, setCards] = useState([])
  const [index, setIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [completed, setCompleted] = useState(false)
  const startRef = useRef(Date.now())

  // Touch swipe state
  const touchStartX = useRef(null)

  const token = session?.access_token

  useEffect(() => {
    async function load() {
      try {
        const l = await api.lessons.get(lessonId)
        setLesson(l)
        setCards(l.content ?? [])
        // Mark as started
        await api.lessons.updateProgress(lessonId, { status: 'in_progress', mode_used: l.mode }, token)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [lessonId, token])

  function prev() { setIndex(i => Math.max(0, i - 1)) }
  function next() {
    if (index < cards.length - 1) {
      setIndex(i => i + 1)
    } else {
      finish()
    }
  }

  async function finish() {
    if (completed) return
    setCompleted(true)
    const seconds = Math.round((Date.now() - startRef.current) / 1000)
    await api.lessons.updateProgress(lessonId, {
      status: 'completed',
      mode_used: lesson?.mode,
      time_spent_seconds: seconds,
    }, token)
    // Show completion for a moment, then go back
    setTimeout(() => navigate(-1), 1500)
  }

  function handleTouchStart(e) { touchStartX.current = e.touches[0].clientX }
  function handleTouchEnd(e) {
    if (touchStartX.current === null) return
    const dx = touchStartX.current - e.changedTouches[0].clientX
    if (Math.abs(dx) > 50) dx > 0 ? next() : prev()
    touchStartX.current = null
  }

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés...</div>
  }

  if (completed) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-gradient-to-b from-turul-blue to-brand-700 text-white px-6">
        <div className="text-6xl">🎉</div>
        <h2 className="text-2xl font-bold">Kész!</h2>
        <p className="text-brand-200">Lecke befejezve</p>
      </div>
    )
  }

  const card = cards[index]
  const progress = cards.length > 0 ? (index + 1) / cards.length : 0

  return (
    <div
      className="flex flex-col h-screen bg-white"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 pt-safe pt-4 pb-2 shrink-0">
        <button
          onClick={() => navigate(-1)}
          className="w-9 h-9 flex items-center justify-center rounded-xl hover:bg-slate-100 text-slate-500"
        >
          ✕
        </button>
        <div className="flex-1 bg-slate-100 rounded-full h-2">
          <div
            className="h-full bg-turul-blue rounded-full transition-all duration-500"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
        <ModeBadge mode={lesson?.mode} />
      </div>

      {/* Card */}
      <div className="flex-1 overflow-hidden">
        {card ? (
          <>
            {lesson?.mode === 'text'   && <TextCard   card={card} />}
            {lesson?.mode === 'story'  && <StoryCard  card={card} />}
            {lesson?.mode === 'visual' && <VisualCard card={card} />}
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            Nincs megjeleníthető tartalom.
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="shrink-0 px-5 pb-safe pb-8 pt-4 flex items-center gap-3">
        <button
          onClick={prev}
          disabled={index === 0}
          className="btn-secondary w-12 h-12 rounded-xl disabled:opacity-30"
        >
          ←
        </button>

        <div className="flex-1 text-center text-sm text-slate-400 font-medium">
          {index + 1} / {cards.length}
        </div>

        <button
          onClick={next}
          className={`btn-primary h-12 px-6 rounded-xl ${
            index === cards.length - 1 ? 'bg-turul-green' : ''
          }`}
        >
          {index === cards.length - 1 ? 'Kész ✓' : '→'}
        </button>
      </div>
    </div>
  )
}
