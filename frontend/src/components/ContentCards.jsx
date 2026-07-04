import { useState } from 'react'

// Shared renderers for NAT 3-tier content_blocks (text | story | visual | quiz | world).

export function TextCard({ card }) {
  return (
    <div className="flex flex-col gap-4 px-6 py-8">
      <h2 className="text-2xl font-bold text-slate-900 leading-snug">{card.heading}</h2>
      <p className="text-slate-700 leading-relaxed">{card.body}</p>
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
  front: 'from-red-900 to-red-700', hátország: 'from-amber-800 to-amber-600',
  gazdaság: 'from-emerald-900 to-emerald-700', otthon: 'from-rose-900 to-rose-700',
  hit: 'from-indigo-900 to-indigo-700', nevelés: 'from-sky-900 to-sky-700',
  iskola: 'from-sky-900 to-sky-700', sebesültek: 'from-slate-800 to-slate-600',
}

export function StoryCard({ card }) {
  const key = (card.mood || '').split(/[\s(]/)[0].toLowerCase()
  const gradient = MOOD_COLORS[key] ?? 'from-slate-800 to-slate-600'
  return (
    <div className={`flex flex-col justify-end bg-gradient-to-b ${gradient} px-6 py-10 gap-4 min-h-[320px] rounded-2xl`}>
      {card.mood && <span className="text-white/60 text-xs font-semibold uppercase tracking-widest">— {card.mood}</span>}
      <h2 className="text-2xl font-bold text-white leading-snug">{card.heading}</h2>
      <p className="text-white/85 leading-relaxed">{card.body}</p>
    </div>
  )
}

const VISUAL_ICONS = { idővonal: '📅', térkép: '🗺️', diagram: '📊', arckép: '🖼️', grafikon: '📈' }

export function VisualCard({ card }) {
  return (
    <div className="flex flex-col gap-4 px-6 py-8">
      <div className="bg-slate-100 rounded-2xl flex flex-col items-center justify-center gap-2 py-10">
        <span className="text-5xl">{VISUAL_ICONS[card.visual_type] ?? '🖼️'}</span>
        <span className="text-slate-500 text-sm font-medium">{card.visual_type}</span>
      </div>
      <h2 className="text-xl font-bold text-slate-900">{card.heading}</h2>
      <p className="text-slate-700 leading-relaxed text-sm">{card.description}</p>
      {card.caption && <p className="text-xs text-slate-400 italic border-t border-slate-100 pt-3">{card.caption}</p>}
    </div>
  )
}

export function WorldCard({ card }) {
  return (
    <div className="flex flex-col gap-3 px-6 py-6 bg-slate-900 rounded-2xl">
      <div className="flex items-center gap-2">
        <span className="text-2xl">🌍</span>
        {card.year && <span className="text-amber-300 font-mono text-sm font-bold">{card.year}</span>}
      </div>
      <h3 className="text-lg font-bold text-white leading-snug">{card.heading}</h3>
      <p className="text-white/80 leading-relaxed text-sm">{card.body}</p>
      {card.link_hu && (
        <p className="text-emerald-300/90 text-sm leading-relaxed border-t border-white/10 pt-3">
          <span className="font-semibold">↪ Nekünk azért fontos: </span>{card.link_hu}
        </p>
      )}
    </div>
  )
}

export function QuizCard({ card }) {
  const [picked, setPicked] = useState(null)
  const correct = (card.correct || '').trim().charAt(0).toUpperCase()
  return (
    <div className="flex flex-col gap-3 px-6 py-6">
      <h3 className="text-lg font-bold text-slate-900 leading-snug">{card.question}</h3>
      <div className="flex flex-col gap-2">
        {(card.options || []).map((opt, i) => {
          const letter = String.fromCharCode(65 + i)
          const isCorrect = letter === correct
          const isPicked = picked === letter
          let cls = 'border-slate-200 bg-white hover:bg-slate-50'
          if (picked) {
            if (isCorrect) cls = 'border-emerald-500 bg-emerald-50'
            else if (isPicked) cls = 'border-red-400 bg-red-50'
            else cls = 'border-slate-200 bg-white opacity-60'
          }
          return (
            <button key={i} onClick={() => !picked && setPicked(letter)} disabled={!!picked}
              className={`text-left px-4 py-3 rounded-xl border font-medium text-slate-700 transition ${cls}`}>
              {opt}
            </button>
          )
        })}
      </div>
      {picked && card.explanation && (
        <p className="text-sm text-slate-600 bg-slate-50 rounded-xl px-4 py-3 mt-1">
          {picked === correct ? '✅ ' : '❌ '}{card.explanation}
        </p>
      )}
    </div>
  )
}

// Scored quiz: per-question reveal on pick, then submit for XP.
export function QuizRunner({ cards, onSubmit }) {
  const [picks, setPicks] = useState({})       // index -> letter
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const list = cards || []
  const correctOf = (c) => (c.correct || '').trim().charAt(0).toUpperCase()
  const answeredCount = Object.keys(picks).length
  const allAnswered = list.length > 0 && answeredCount >= list.length

  async function submit() {
    if (busy || result) return
    setBusy(true)
    try {
      const answers = list.map((_, i) => picks[i] || '')
      setResult(await onSubmit(answers))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {list.map((card, qi) => {
        const correct = correctOf(card)
        const picked = picks[qi]
        return (
          <div key={qi} className="bg-white rounded-2xl shadow-sm border border-slate-100 px-6 py-6 flex flex-col gap-3">
            <h3 className="text-lg font-bold text-slate-900 leading-snug">{card.question}</h3>
            <div className="flex flex-col gap-2">
              {(card.options || []).map((opt, i) => {
                const letter = String.fromCharCode(65 + i)
                let cls = 'border-slate-200 bg-white hover:bg-slate-50'
                if (picked) {
                  if (letter === correct) cls = 'border-emerald-500 bg-emerald-50'
                  else if (letter === picked) cls = 'border-red-400 bg-red-50'
                  else cls = 'border-slate-200 bg-white opacity-60'
                }
                return (
                  <button key={i} disabled={!!picked || !!result}
                    onClick={() => setPicks(p => ({ ...p, [qi]: letter }))}
                    className={`text-left px-4 py-3 rounded-xl border font-medium text-slate-700 transition ${cls}`}>
                    {opt}
                  </button>
                )
              })}
            </div>
            {picked && card.explanation && (
              <p className="text-sm text-slate-600 bg-slate-50 rounded-xl px-4 py-3">
                {picked === correct ? '✅ ' : '❌ '}{card.explanation}
              </p>
            )}
          </div>
        )
      })}

      {result ? (
        <div className="rounded-2xl p-5 bg-turul-blue text-white text-center shadow-glow-blue">
          <p className="text-3xl font-extrabold font-display">{result.correct}/{result.total}</p>
          <p className="text-brand-100 text-sm mt-0.5">{result.score}% · +{result.xp_earned} XP</p>
        </div>
      ) : (
        <button onClick={submit} disabled={!allAnswered || busy}
          className="btn-primary h-12 rounded-xl disabled:opacity-40">
          {busy ? '…' : allAnswered ? 'Beküldés' : `Válaszolj mind (${answeredCount}/${list.length})`}
        </button>
      )}
    </div>
  )
}

export function CardList({ mode, cards }) {
  const Renderer = { text: TextCard, story: StoryCard, visual: VisualCard, world: WorldCard, quiz: QuizCard }[mode]
  if (!Renderer) return null
  return (
    <div className="flex flex-col gap-4">
      {(cards || []).map((c, i) => (
        <div key={i} className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <Renderer card={c} />
        </div>
      ))}
    </div>
  )
}
