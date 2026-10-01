import { useLang } from '../contexts/LanguageContext'
import { useNarration } from '../lib/useNarration'
import NarrationIcon from './NarrationIcon'

// „Felolvasás”. variant="card": reads from this card on, to the end of its list (the tab);
// variant="lesson": reads the whole list from the top, like starting an audiobook.
// queue = { id, title, items: [{ title, text, audio } | null, …] } index-aligned with the cards.
export default function ReadAloudButton({ queue, index = 0, variant = 'card' }) {
  const { t } = useLang()
  const { narrator, state } = useNarration()
  if (!queue) return null
  const playable = variant === 'card' ? narrator.canPlay(queue.items[index]) : narrator.canPlayQueue(queue)
  if (!playable) return null

  const mine = state.queueId === queue.id && state.status !== 'idle'
  const active = mine && (variant === 'lesson' || state.index === index)
  const paused = active && state.status === 'paused'
  const idleLabel = t(variant === 'lesson' ? 'listen.lesson' : 'listen.card')
  const label = !active ? idleLabel : paused ? t('listen.resume') : t('listen.pause')
  const icon = !active ? (variant === 'lesson' ? '🎧' : '🔊') : <NarrationIcon name={paused ? 'play' : 'pause'} size={14} />

  const onClick = () => (active ? narrator.toggle() : narrator.play(queue, index))
  const cls = variant === 'lesson'
    ? 'w-full flex items-center justify-center gap-2 rounded-xl px-4 py-3 font-semibold text-sm transition '
      + (active ? 'bg-turul-blue text-white' : 'bg-turul-blue/10 text-turul-blue hover:bg-turul-blue/15')
    : 'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-turul-blue hover:bg-brand-50 transition'

  return (
    <button type="button" onClick={onClick} className={cls} aria-pressed={active && !paused}>
      <span aria-hidden="true" className="inline-flex">{icon}</span>
      <span>{label}</span>
    </button>
  )
}
