import { useLang } from '../contexts/LanguageContext'

const MODE_CONFIG = {
  text:   { key: 'mode.text',   emoji: '📖', bg: 'bg-blue-100',   text: 'text-blue-700' },
  story:  { key: 'mode.story',  emoji: '🎭', bg: 'bg-purple-100', text: 'text-purple-700' },
  visual: { key: 'mode.visual', emoji: '🗺️',  bg: 'bg-amber-100',  text: 'text-amber-700' },
  quiz:   { key: 'mode.quiz',   emoji: '🧠', bg: 'bg-green-100',  text: 'text-green-700' },
}

export default function ModeBadge({ mode, size = 'sm' }) {
  const { t } = useLang()
  const cfg = MODE_CONFIG[mode] ?? { key: null, emoji: '📄', bg: 'bg-slate-100', text: 'text-slate-600' }
  const label = cfg.key ? t(cfg.key) : mode
  const padding = size === 'lg' ? 'px-4 py-2 text-sm' : 'px-2.5 py-1 text-xs'

  return (
    <span className={`mode-pill ${cfg.bg} ${cfg.text} ${padding}`}>
      {cfg.emoji} {label}
    </span>
  )
}
