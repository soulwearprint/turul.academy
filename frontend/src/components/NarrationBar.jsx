import { useLocation } from 'react-router-dom'
import { useLang } from '../contexts/LanguageContext'
import { useNarration } from '../lib/useNarration'
import NarrationIcon from './NarrationIcon'

// The audiobook player: appears while something is being read, on every page, so a lesson keeps
// going (and can be paused or skipped) after the student has left its page. On the lock screen
// the same controls come from the Media Session API (lib/narration.js).
// The legacy card player (/lessons/:id) has its own controls in its top bar.
export default function NarrationBar() {
  const { t } = useLang()
  const { narrator, state } = useNarration()
  const { pathname } = useLocation()
  if (state.status === 'idle' || /^\/lessons\/[^/]+$/.test(pathname)) return null

  const paused = state.status === 'paused'
  const btn = 'w-9 h-9 shrink-0 flex items-center justify-center rounded-full hover:bg-white/10 text-white/80 text-sm'
  return (
    <div className="narration-bar fixed inset-x-0 z-[60] px-3 pointer-events-none" role="region" aria-label={t('listen.bar')}>
      <div className="pointer-events-auto max-w-2xl mx-auto bg-slate-900 text-white rounded-2xl shadow-lg px-2.5 py-2 flex items-center gap-1.5">
        <button type="button" onClick={() => narrator.toggle()} aria-label={paused ? t('listen.resume') : t('listen.pause')}
          className="w-11 h-11 shrink-0 flex items-center justify-center rounded-full bg-turul-blue text-lg">
          {state.status === 'loading' ? <span className="animate-pulse text-xl leading-none">…</span> : <NarrationIcon name={paused ? 'play' : 'pause'} size={20} />}
        </button>
        <div className="min-w-0 flex-1 px-1">
          <p className="text-sm font-semibold truncate">{state.title || state.queueTitle}</p>
          <p className="text-[11px] text-white/60 truncate">
            {state.queueTitle} · {state.index + 1}/{state.total}
          </p>
          {state.engine === 'speech' && (
            <p className="text-[11px] text-amber-300 leading-tight">{t('listen.browser.voice')}</p>
          )}
        </div>
        <button type="button" onClick={() => narrator.prev()} className={btn} aria-label={t('listen.prev')}><NarrationIcon name="prev" /></button>
        <button type="button" onClick={() => narrator.next()} className={btn} aria-label={t('listen.next')}><NarrationIcon name="next" /></button>
        <button type="button" onClick={() => narrator.cycleRate()} className={`${btn} text-xs font-bold tabular-nums w-11`}
          aria-label={t('listen.speed')}>{state.rate}×</button>
        <button type="button" onClick={() => narrator.stop()} className={btn} aria-label={t('listen.stop')}><NarrationIcon name="close" size={16} /></button>
      </div>
    </div>
  )
}
