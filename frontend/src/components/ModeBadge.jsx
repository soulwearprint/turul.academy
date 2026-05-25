const MODE_CONFIG = {
  text:   { label: 'Szöveg',   emoji: '📖', bg: 'bg-blue-100',   text: 'text-blue-700' },
  story:  { label: 'Történet', emoji: '🎭', bg: 'bg-purple-100', text: 'text-purple-700' },
  visual: { label: 'Vizuális', emoji: '🗺️',  bg: 'bg-amber-100',  text: 'text-amber-700' },
  quiz:   { label: 'Kvíz',     emoji: '🧠', bg: 'bg-green-100',  text: 'text-green-700' },
}

export default function ModeBadge({ mode, size = 'sm' }) {
  const cfg = MODE_CONFIG[mode] ?? { label: mode, emoji: '📄', bg: 'bg-slate-100', text: 'text-slate-600' }
  const padding = size === 'lg' ? 'px-4 py-2 text-sm' : 'px-2.5 py-1 text-xs'

  return (
    <span className={`mode-pill ${cfg.bg} ${cfg.text} ${padding}`}>
      {cfg.emoji} {cfg.label}
    </span>
  )
}
