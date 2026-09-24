import { useEffect, useRef, useState } from 'react'

// Active study time on one lesson visit, split by tab (mode).
//
// Counts only while the page is visible AND the student has touched/scrolled/typed
// within IDLE_MS — a lesson left open on the desk isn't study. Nothing is sent until
// DWELL_MS of active time: a lesson opened by mistake and left within 10s leaves no
// trace (no "Started" status, no time). After that, deltas are flushed periodically,
// when the tab is hidden, and when the student leaves the lesson.
const TICK_MS = 1000
const IDLE_MS = 120_000
const DWELL_MS = 10_000
const FLUSH_MS = 60_000
const MAX_TICK_MS = 5_000   // a throttled/suspended timer must not count a long gap
const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'wheel', 'touchstart', 'scroll', 'mousemove']

export function useStudyTimer({ mode, onFlush, enabled = true }) {
  const [engaged, setEngaged] = useState(false)
  const modeRef = useRef(mode)
  const flushRef = useRef(onFlush)
  flushRef.current = onFlush
  const enabledRef = useRef(enabled)       // e.g. false while the lesson is still loading
  enabledRef.current = enabled

  const s = useRef(null)
  if (!s.current) {
    const now = Date.now()
    s.current = { pending: {}, totalMs: 0, lastTick: now, lastInput: now }
  }

  function tick() {
    const st = s.current
    const now = Date.now()
    const dt = Math.min(now - st.lastTick, MAX_TICK_MS)
    st.lastTick = now
    if (!enabledRef.current || document.visibilityState !== 'visible' || now - st.lastInput > IDLE_MS) return
    const m = modeRef.current
    st.pending[m] = (st.pending[m] || 0) + dt
    st.totalMs += dt
    if (st.totalMs >= DWELL_MS) setEngaged(true)
  }

  function flush() {
    const st = s.current
    tick()
    if (st.totalMs < DWELL_MS) return        // mis-tap: never recorded
    const modes = {}
    let seconds = 0
    for (const [m, ms] of Object.entries(st.pending)) {
      const sec = Math.floor(ms / 1000)
      if (sec > 0) { modes[m] = sec; seconds += sec }
      st.pending[m] = ms - sec * 1000        // keep the sub-second remainder
    }
    if (seconds > 0) flushRef.current?.({ time_spent_seconds: seconds, mode_seconds: modes })
  }

  // Attribute time up to the switch to the tab being left.
  useEffect(() => {
    if (modeRef.current !== mode) { tick(); modeRef.current = mode }
  }, [mode])

  useEffect(() => {
    const markInput = () => { s.current.lastInput = Date.now() }
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') flush()
      else { s.current.lastTick = Date.now(); markInput() }
    }
    ACTIVITY_EVENTS.forEach(e => window.addEventListener(e, markInput, { passive: true, capture: true }))
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('pagehide', flush)
    const ticker = setInterval(tick, TICK_MS)
    const flusher = setInterval(flush, FLUSH_MS)
    return () => {
      ACTIVITY_EVENTS.forEach(e => window.removeEventListener(e, markInput, { capture: true }))
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pagehide', flush)
      clearInterval(ticker)
      clearInterval(flusher)
      flush()                                 // leaving the lesson (in-app navigation)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return { engaged }
}
