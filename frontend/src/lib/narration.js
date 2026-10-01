// „Felolvasás” — one narrator for the whole app (audiobook mode).
//
// A queue is a list of cards (a lesson tab, one deep dive, one quiz question). Each item is
// { title, text, audio } where `audio` is the Storage path of a pre-generated mp3 (or null).
//
//  • item has `audio`  → one <audio> element + Media Session. This is the only thing mobile
//    browsers keep playing with the screen locked or the app in the background, and it gives
//    lock-screen / headphone controls (play, pause, next card, previous card).
//  • no `audio` file   → the browser's own voice (speechSynthesis, hu-HU). Works on screen only:
//    iOS and most Android browsers stop it when the page is hidden or the screen locks. Used
//    for cards whose audio hasn't been generated yet and for quiz questions.
//
// The narrator is framework-free (React talks to it through useSyncExternalStore, see
// contexts/NarrationContext.jsx) and takes every browser API as an injectable, so
// frontend/src/lib/narration.test.mjs can drive it under plain Node.

export const RATES = [0.85, 1, 1.2, 1.5]
const RATE_KEY = 'ta_narration_rate'
const SPEECH_LANG = 'hu-HU'
const SPEECH_CHUNK = 220          // chars per utterance: long ones get cut off by some engines
const RESTART_AFTER = 3           // "previous" within the first 3 s of a card restarts it instead

/** Sentences of one line. A full stop right after a digit ("1848. március", "28.") or inside a token
 *  ("3.14") is not a sentence end — splitting there would put a pause inside a date or an ordinal. */
function sentences(line) {
  const out = []
  let start = 0
  for (let i = 0; i < line.length; i++) {
    const c = line[i]
    if (c !== '.' && c !== '!' && c !== '?' && c !== '…') continue
    if (c === '.' && /\d/.test(line[i - 1] || '')) continue
    let j = i + 1
    while (j < line.length && /["”’)\]]/.test(line[j])) j++
    if (j < line.length && !/\s/.test(line[j])) continue
    out.push(line.slice(start, j).trim())
    start = j
    i = j - 1
  }
  if (line.slice(start).trim()) out.push(line.slice(start).trim())
  return out
}

/** Sentence-sized pieces (≤ max chars) so no single utterance runs long. */
export function splitForSpeech(text, max = SPEECH_CHUNK) {
  const out = []
  for (const line of String(text || '').split(/\n+/)) {
    let cur = ''
    for (const sentence of sentences(line)) {
      if (cur && cur.length + 1 + sentence.length > max) { out.push(cur); cur = '' }
      cur = cur ? `${cur} ${sentence}` : sentence
      while (cur.length > max) {
        let cut = cur.lastIndexOf(' ', max)
        if (cut <= 0) cut = max
        out.push(cur.slice(0, cut))
        cur = cur.slice(cut).trim()
      }
    }
    if (cur.trim()) out.push(cur.trim())
  }
  return out
}

function readRate(storage) {
  try {
    const r = Number(storage?.getItem(RATE_KEY))
    return RATES.includes(r) ? r : 1
  } catch { return 1 }
}

export class Narrator {
  constructor(env = {}) {
    const g = globalThis
    this.env = {
      Audio: env.Audio ?? g.Audio,
      synth: env.synth ?? g.speechSynthesis,
      Utterance: env.Utterance ?? g.SpeechSynthesisUtterance,
      MediaMetadata: env.MediaMetadata ?? g.MediaMetadata,
      mediaSession: env.mediaSession ?? g.navigator?.mediaSession,
      resolveUrl: env.resolveUrl ?? (x => x),
      storage: env.storage ?? (() => { try { return g.localStorage } catch { return null } })(),
      doc: env.doc ?? g.document,
    }
    this.listeners = new Set()
    this.token = 0              // bumped on every (re)start/cancel: callbacks of an older start are ignored
    this.audio = null
    this.chunk = 0              // speech: chunk to (re)start from
    this.expectPause = 0
    this.voice = null
    this.state = { status: 'idle', queueId: null, queueTitle: '', title: '', index: -1, total: 0,
                   engine: null, rate: readRate(this.env.storage), voiceMissing: false }
    this.queue = null
    this.subscribe = this.subscribe.bind(this)
    this.getSnapshot = this.getSnapshot.bind(this)
    this.env.synth?.addEventListener?.('voiceschanged', () => { this.voice = null; this._publish() })
    this.env.doc?.addEventListener?.('visibilitychange', () => this._onVisible())
  }

  // ── store ────────────────────────────────────────────────
  subscribe(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn) }
  getSnapshot() { return this.state }
  _set(patch) {
    this.state = { ...this.state, ...patch }
    this._syncMediaSession()
    this.listeners.forEach(fn => fn())
  }
  _publish() { this._set({ voiceMissing: !this.speechOk() }) }

  // ── what can be played ───────────────────────────────────
  _voice() {
    if (this.voice) return this.voice
    const list = this.env.synth?.getVoices?.() || []
    this.voice = list.find(v => /^hu([-_]|$)/i.test(v.lang || '')) || null
    return this.voice
  }
  /** Is there a Hungarian browser voice? An empty voice list (Android Chrome fills it late) counts as yes. */
  speechOk() {
    if (!this.env.synth || !this.env.Utterance) return false
    const list = this.env.synth.getVoices?.() || []
    return list.length === 0 || !!this._voice()
  }
  canPlay(item) { return !!(item && item.text && (item.audio ? this.env.Audio : this.speechOk())) }
  _playableFrom(items, from, step) {
    for (let i = from; i >= 0 && i < items.length; i += step) if (this.canPlay(items[i])) return i
    return -1
  }
  canPlayQueue(queue) { return this._playableFrom(queue?.items || [], 0, 1) >= 0 }

  // ── transport ────────────────────────────────────────────
  /** Start `queue` ({id, title, items}) at card `index` (or the next playable one). Call from a tap. */
  play(queue, index = 0) {
    const i = this._playableFrom(queue?.items || [], index, 1)
    if (i < 0) return false
    this._stopOutput()
    this.queue = queue
    this.chunk = 0
    this._setupMediaSession()
    this._begin(i)
    return true
  }

  _begin(i) {
    const item = this.queue.items[i]
    this._set({ status: 'loading', queueId: this.queue.id, queueTitle: this.queue.title || '', title: item.title || '',
                index: i, total: this.queue.items.length, engine: item.audio && this.env.Audio ? 'audio' : 'speech',
                voiceMissing: !this.speechOk() })
    if (item.audio && this.env.Audio) this._playAudio(item)
    else this._playSpeech(item)
  }

  /** pause() whose `pause` event we expect and must not mistake for the lock screen pausing. */
  _pauseAudio() {
    const a = this.audio
    if (a && !a.paused) { this.expectPause++; a.pause() }
  }

  _stopOutput() {
    this.token++
    this._pauseAudio()
    try { this.env.synth?.cancel() } catch { /* nothing speaking */ }
  }

  pause() {
    if (this.state.status === 'idle' || this.state.status === 'paused') return
    if (this.state.engine === 'audio') {
      this._pauseAudio()
      this._set({ status: 'paused' })
    } else {
      this.token++                             // speech can't pause reliably everywhere: stop, resume at this sentence
      this.env.synth?.cancel()
      this._set({ status: 'paused' })
    }
  }

  resume() {
    if (this.state.status !== 'paused' || !this.queue) return
    const item = this.queue.items[this.state.index]
    if (this.state.engine === 'audio' && this.audio?.src) {
      if (!this.audio.paused) return this._set({ status: 'playing' })
      this._set({ status: 'loading' })
      this.audio.play().catch(() => this._set({ status: 'paused' }))
    } else {
      this._begin(this.state.index)            // speech restarts at the sentence it was in (this.chunk)
    }
    return item
  }

  toggle() { return this.state.status === 'paused' ? this.resume() : this.pause() }

  next() {
    if (!this.queue) return
    this.chunk = 0
    const i = this._playableFrom(this.queue.items, this.state.index + 1, 1)
    if (i < 0) return this.stop()
    this._stopOutput()
    this._begin(i)
  }

  prev() {
    if (!this.queue) return
    if (this.state.engine === 'audio' && this.audio && this.audio.currentTime > RESTART_AFTER) {
      this.audio.currentTime = 0
      return
    }
    const i = this._playableFrom(this.queue.items, this.state.index - 1, -1)
    this.chunk = 0
    this._stopOutput()
    this._begin(i < 0 ? this.state.index : i)
  }

  stop() {
    this._stopOutput()
    this.queue = null
    this.chunk = 0
    this._set({ status: 'idle', queueId: null, queueTitle: '', title: '', index: -1, total: 0, engine: null })
    try { if (this.audio) this.audio.removeAttribute('src') } catch { /* ignore */ }
  }

  setRate(rate) {
    if (!RATES.includes(rate)) return
    try { this.env.storage?.setItem(RATE_KEY, String(rate)) } catch { /* private mode */ }
    if (this.audio) this.audio.playbackRate = rate
    this._set({ rate })
    if (this.state.engine === 'speech' && this.state.status === 'playing') {
      this._stopOutput()                       // the new speed applies from the current sentence
      this._begin(this.state.index)
    }
  }

  cycleRate() {
    this.setRate(RATES[(RATES.indexOf(this.state.rate) + 1) % RATES.length])
  }

  // ── audio engine ─────────────────────────────────────────
  _audioEl() {
    if (this.audio) return this.audio
    const a = new this.env.Audio()
    a.preload = 'auto'
    // Events carry no token: they describe the element, and the element only ever plays the current card.
    a.addEventListener('playing', () => { if (this.state.engine === 'audio' && this.queue) this._set({ status: 'playing' }) })
    a.addEventListener('waiting', () => { if (this.state.engine === 'audio' && this.state.status === 'playing') this._set({ status: 'loading' }) })
    // Paused from outside (lock screen, headphones, another app took audio focus).
    a.addEventListener('pause', () => {
      if (this.expectPause > 0) { this.expectPause--; return }
      if (this.state.engine === 'audio' && this.queue && !a.ended && this.state.status !== 'idle') this._set({ status: 'paused' })
    })
    a.addEventListener('ended', () => { if (this.state.engine === 'audio' && this.queue) this._advance() })
    a.addEventListener('error', () => {
      if (this.state.engine !== 'audio' || !this.queue) return
      const item = this.queue.items[this.state.index]
      if (item?.text && this.speechOk()) {     // file missing / offline → the browser voice reads this card instead
        this.token++
        this._set({ engine: 'speech', status: 'loading' })
        this._playSpeech(item)
      } else {
        this._advance()
      }
    })
    this.audio = a
    return a
  }

  _playAudio(item) {
    const a = this._audioEl()
    a.src = this.env.resolveUrl(item.audio)
    a.playbackRate = this.state.rate
    const token = this.token
    const p = a.play()
    p?.catch?.(err => {
      if (token !== this.token) return
      // Autoplay refused (no tap behind this start): wait, the person can press play.
      if (err?.name === 'NotAllowedError') this._set({ status: 'paused' })
      // Anything else surfaces as the element's `error` event.
    })
  }

  // ── speech engine ────────────────────────────────────────
  _playSpeech(item) {
    const synth = this.env.synth
    if (!synth || !this.env.Utterance) return this._advance()
    this._set({ engine: 'speech' })
    const token = ++this.token
    const chunks = splitForSpeech(item.text)
    const speak = () => {
      if (token !== this.token) return
      if (this.chunk >= chunks.length) { this.chunk = 0; return this._advance() }
      const u = new this.env.Utterance(chunks[this.chunk])
      u.lang = SPEECH_LANG
      u.rate = this.state.rate
      const v = this._voice()
      if (v) u.voice = v
      u.onstart = () => { if (token === this.token) this._set({ status: 'playing' }) }
      u.onend = () => { if (token === this.token) { this.chunk++; speak() } }
      u.onerror = (e) => {
        if (token !== this.token || e?.error === 'canceled' || e?.error === 'interrupted') return
        this._set({ status: 'paused' })        // e.g. no voice: show ▶ instead of pretending to play
      }
      synth.speak(u)
    }
    speak()
  }

  _advance() {
    this.chunk = 0
    const i = this._playableFrom(this.queue.items, this.state.index + 1, 1)
    if (i < 0) return this.stop()
    this._begin(i)
  }

  /** Back on screen: if the browser killed the speech while hidden, show ▶ rather than a lying ⏸. */
  _onVisible() {
    if (this.env.doc?.visibilityState !== 'visible') return
    const s = this.env.synth
    if (this.state.engine === 'speech' && this.state.status === 'playing' && s && !s.speaking && !s.pending) {
      this.token++
      this._set({ status: 'paused' })
    }
  }

  // ── lock screen / headphones ─────────────────────────────
  _setupMediaSession() {
    const ms = this.env.mediaSession
    if (!ms || this.msReady) return
    this.msReady = true
    const handlers = { play: () => this.resume(), pause: () => this.pause(), stop: () => this.stop(),
                       previoustrack: () => this.prev(), nexttrack: () => this.next(),
                       seekbackward: null, seekforward: null }   // so iOS shows ⏮ ⏭ (cards), not ±10 s
    for (const [action, fn] of Object.entries(handlers)) {
      try { ms.setActionHandler(action, fn) } catch { /* action not supported here */ }
    }
  }

  _syncMediaSession() {
    const ms = this.env.mediaSession
    if (!ms) return
    const { status, title, queueTitle } = this.state
    try {
      if (status === 'idle') { ms.metadata = null; ms.playbackState = 'none'; return }
      if (this.env.MediaMetadata && (!ms.metadata || ms.metadata.title !== title)) {
        ms.metadata = new this.env.MediaMetadata({
          title: title || queueTitle, artist: 'Turul Academy', album: queueTitle,
          artwork: [{ src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
                    { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }],
        })
      }
      ms.playbackState = status === 'paused' ? 'paused' : 'playing'
    } catch { /* Media Session is a nicety, never a reason to fail */ }
  }
}
