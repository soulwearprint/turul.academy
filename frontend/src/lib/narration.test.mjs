// node --test src/lib/narration.test.mjs   (the narrator with fake Audio / speechSynthesis / Media Session)
import test from 'node:test'
import assert from 'node:assert/strict'
import { Narrator, splitForSpeech, RATES } from './narration.js'

const tick = () => new Promise(r => setTimeout(r, 0))

class FakeAudio {
  constructor() { this.l = {}; this.paused = true; this.ended = false; this.currentTime = 0; this.src = ''; this.playbackRate = 1; FakeAudio.last = this }
  addEventListener(t, f) { (this.l[t] ||= []).push(f) }
  emit(t) { (this.l[t] || []).forEach(f => f()) }
  play() { this.paused = false; this.ended = false; queueMicrotask(() => this.emit('playing')); return Promise.resolve() }
  pause() { if (!this.paused) { this.paused = true; queueMicrotask(() => this.emit('pause')) } }
  removeAttribute() { this.src = '' }
  finish() { this.ended = true; this.paused = true; this.emit('ended') }     // test helper: the file played to the end
}

function fakeSynth(voices = [{ lang: 'hu-HU', name: 'Mariska' }]) {
  const s = { voices, spoken: [], cancelled: 0, speaking: false, pending: false, utter: null,
    getVoices() { return this.voices }, addEventListener() {},
    speak(u) { this.spoken.push(u.text); this.utter = u; this.speaking = true; queueMicrotask(() => u.onstart?.()) },
    cancel() { this.cancelled++; this.speaking = false; const u = this.utter; this.utter = null; u?.onerror?.({ error: 'canceled' }) },
    finish() { const u = this.utter; this.speaking = false; this.utter = null; u?.onend?.() } }
  return s
}

function makeMediaSession() {
  const handlers = {}
  return { handlers, metadata: null, playbackState: 'none', setActionHandler(a, f) { handlers[a] = f } }
}

function setup({ synth = fakeSynth(), withAudio = true } = {}) {
  const mediaSession = makeMediaSession()
  const store = {}
  const n = new Narrator({
    Audio: withAudio ? FakeAudio : undefined, synth, Utterance: class { constructor(t) { this.text = t } },
    MediaMetadata: class { constructor(o) { Object.assign(this, o) } }, mediaSession,
    resolveUrl: p => `https://cdn.test/${p}`, storage: { getItem: k => store[k] ?? null, setItem: (k, v) => { store[k] = v } },
    doc: { addEventListener() {}, visibilityState: 'visible' },
  })
  return { n, synth, mediaSession, store }
}

const card = (title, audio = null, text = `${title}.`) => ({ title, text, audio })
const Q = (items, id = 'L1:text') => ({ id, title: 'Sebesség', items })

test('splitForSpeech keeps dates and ordinals in one piece and respects the limit', () => {
  assert.deepEqual(splitForSpeech('1848. március 15. volt. Aztán jött a következő nap!'), ['1848. március 15. volt. Aztán jött a következő nap!'])
  const long = Array.from({ length: 40 }, (_, i) => `Ez a ${i}. mondat.`).join(' ')
  const parts = splitForSpeech(long, 100)
  assert.ok(parts.length > 3 && parts.every(p => p.length <= 100))
  assert.equal(parts.join(' ').replace(/\s+/g, ' '), long)
  assert.deepEqual(splitForSpeech('Cím.\n\nSzöveg itt.'), ['Cím.', 'Szöveg itt.'])
  assert.deepEqual(splitForSpeech('Pi = 3.14 körülbelül. Jó.', 24), ['Pi = 3.14 körülbelül.', 'Jó.'])
  assert.deepEqual(splitForSpeech('x'.repeat(50), 20).join(''), 'x'.repeat(50))
})

test('an audio queue plays card after card and ends idle, clearing the lock-screen entry', async () => {
  const { n, mediaSession } = setup()
  assert.ok(n.play(Q([card('A', 'content-audio/a.mp3'), card('B', 'content-audio/b.mp3')])))
  assert.equal(n.getSnapshot().status, 'loading')
  assert.equal(FakeAudio.last.src, 'https://cdn.test/content-audio/a.mp3')
  await tick()
  assert.equal(n.getSnapshot().status, 'playing')
  assert.equal(n.getSnapshot().engine, 'audio')
  assert.equal(mediaSession.metadata.title, 'A')
  assert.equal(mediaSession.metadata.artist, 'Turul Academy')
  assert.equal(mediaSession.playbackState, 'playing')

  FakeAudio.last.finish()                                   // card A ended → card B starts by itself
  assert.equal(n.getSnapshot().index, 1)
  assert.equal(FakeAudio.last.src, 'https://cdn.test/content-audio/b.mp3')
  await tick()
  FakeAudio.last.finish()                                   // last card ended
  assert.equal(n.getSnapshot().status, 'idle')
  assert.equal(mediaSession.metadata, null)
  assert.equal(mediaSession.playbackState, 'none')
})

test('the same <audio> element is reused for every card (what keeps iOS playing while locked)', async () => {
  const { n } = setup()
  n.play(Q([card('A', 'a.mp3'), card('B', 'b.mp3'), card('C', 'c.mp3')]))
  const el = FakeAudio.last
  await tick(); el.finish(); await tick(); el.finish()
  assert.equal(FakeAudio.last, el)
})

test('lock-screen pause and play drive the narrator through Media Session', async () => {
  const { n, mediaSession } = setup()
  n.play(Q([card('A', 'a.mp3')]))
  await tick()
  mediaSession.handlers.pause()
  assert.equal(n.getSnapshot().status, 'paused')
  assert.equal(mediaSession.playbackState, 'paused')
  await tick()
  mediaSession.handlers.play()
  await tick()
  assert.equal(n.getSnapshot().status, 'playing')
  assert.equal(mediaSession.handlers.seekbackward, null)    // so iOS offers ⏮ ⏭ for cards
  assert.equal(typeof mediaSession.handlers.nexttrack, 'function')
})

test('the element paused from outside (headphones unplugged) shows as paused', async () => {
  const { n } = setup()
  n.play(Q([card('A', 'a.mp3')]))
  await tick()
  FakeAudio.last.pause()                                    // not us
  await tick()
  assert.equal(n.getSnapshot().status, 'paused')
})

test('next() mid-playback never flashes a paused state for the new card', async () => {
  const { n } = setup()
  const seen = []
  n.subscribe(() => seen.push(n.getSnapshot().status))
  n.play(Q([card('A', 'a.mp3'), card('B', 'b.mp3')]))
  await tick()
  seen.length = 0
  n.next()
  await tick(); await tick()
  assert.ok(!seen.includes('paused'), seen.join(','))
  assert.equal(n.getSnapshot().index, 1)
  assert.equal(n.getSnapshot().status, 'playing')
})

test('previous restarts a card that has played for a while, else goes back', async () => {
  const { n } = setup()
  n.play(Q([card('A', 'a.mp3'), card('B', 'b.mp3')]), 1)
  await tick()
  FakeAudio.last.currentTime = 12
  n.prev()
  assert.equal(n.getSnapshot().index, 1)
  assert.equal(FakeAudio.last.currentTime, 0)
  n.prev()
  assert.equal(n.getSnapshot().index, 0)
})

test('cards with nothing to say are skipped, and a queue with nothing playable is refused', () => {
  const { n } = setup()
  assert.equal(n.play(Q([null, { title: 'x', text: '', audio: null }])), false)
  assert.equal(n.getSnapshot().status, 'idle')
  assert.ok(n.play(Q([null, card('B', 'b.mp3')])))
  assert.equal(n.getSnapshot().index, 1)
})

test('a refused queue leaves what is already playing alone', async () => {
  const { n } = setup()
  n.play(Q([card('A', 'a.mp3')]))
  await tick()
  assert.equal(n.play(Q([null], 'other')), false)
  assert.equal(n.getSnapshot().queueId, 'L1:text')
  assert.equal(n.getSnapshot().status, 'playing')
})

test('without an audio file the browser voice reads sentence by sentence; pause resumes at that sentence', async () => {
  const { n, synth } = setup()
  n.play(Q([card('A', null, 'Első mondat. Második mondat.\nHarmadik.')]))
  assert.equal(n.getSnapshot().engine, 'speech')
  assert.deepEqual(synth.spoken, ['Első mondat. Második mondat.'])
  await tick()
  assert.equal(n.getSnapshot().status, 'playing')
  synth.finish()                                            // chunk 1 done → chunk 2
  assert.deepEqual(synth.spoken, ['Első mondat. Második mondat.', 'Harmadik.'])
  n.pause()                                                 // cancel() fires onerror('canceled'): must be ignored
  assert.equal(n.getSnapshot().status, 'paused')
  n.resume()
  assert.deepEqual(synth.spoken.slice(-1), ['Harmadik.'])   // same sentence again, not from the top
  await tick()
  synth.finish()
  assert.equal(n.getSnapshot().status, 'idle')
})

test('a stale utterance callback after skipping to the next card does nothing', async () => {
  const { n, synth } = setup()
  n.play(Q([card('A', null, 'Egy. Kettő.'), card('B', null, 'Három.')]))
  const stale = synth.utter
  n.next()
  assert.equal(n.getSnapshot().index, 1)
  stale.onend?.()
  assert.equal(n.getSnapshot().index, 1)
  assert.deepEqual(synth.spoken, ['Egy. Kettő.', 'Három.'])
})

test('mixed queue: audio card, then a card without audio read by the browser voice', async () => {
  const { n, synth } = setup()
  n.play(Q([card('A', 'a.mp3'), card('B', null, 'Béla szól.')]))
  await tick()
  FakeAudio.last.finish()
  assert.equal(n.getSnapshot().engine, 'speech')
  assert.deepEqual(synth.spoken, ['Béla szól.'])
})

test('a broken audio file falls back to the browser voice for that card', async () => {
  const { n, synth } = setup()
  n.play(Q([card('A', 'missing.mp3', 'Szöveg.')]))
  FakeAudio.last.emit('error')
  assert.equal(n.getSnapshot().engine, 'speech')
  assert.deepEqual(synth.spoken, ['Szöveg.'])
})

test('no Hungarian voice and no audio file: nothing to play, and the UI can tell', () => {
  const { n } = setup({ synth: fakeSynth([{ lang: 'en-US', name: 'Samantha' }]) })
  assert.equal(n.speechOk(), false)
  assert.equal(n.canPlay(card('A', null)), false)
  assert.equal(n.canPlay(card('A', 'a.mp3')), true)
  assert.equal(n.play(Q([card('A', null)])), false)
})

test('an empty voice list (Android Chrome loads it late) is treated as available', () => {
  const { n } = setup({ synth: fakeSynth([]) })
  assert.equal(n.speechOk(), true)
})

test('speech killed by the browser while the page was hidden shows as paused when it comes back', async () => {
  const { n, synth } = setup()
  const doc = { listeners: [], addEventListener(_, f) { this.listeners.push(f) }, visibilityState: 'visible' }
  const m = new Narrator({ Audio: FakeAudio, synth, Utterance: class { constructor(t) { this.text = t } }, doc,
    storage: { getItem: () => null, setItem() {} } })
  m.play(Q([card('A', null, 'Hosszú szöveg.')]))
  await tick()
  assert.equal(m.getSnapshot().status, 'playing')
  synth.speaking = false                                    // the OS silenced it while the screen was off
  doc.listeners.forEach(f => f())
  assert.equal(m.getSnapshot().status, 'paused')
  void n
})

test('speed is remembered and applied to audio', async () => {
  const { n, store } = setup()
  n.play(Q([card('A', 'a.mp3')]))
  n.cycleRate()
  assert.equal(n.getSnapshot().rate, RATES[2])
  assert.equal(FakeAudio.last.playbackRate, RATES[2])
  assert.equal(store.ta_narration_rate, String(RATES[2]))
  n.setRate(7)                                              // not an offered speed → ignored
  assert.equal(n.getSnapshot().rate, RATES[2])
})

test('stop() ends everything and no autoplay-blocked promise leaves it stuck', async () => {
  const { n } = setup()
  n.play(Q([card('A', 'a.mp3')]))
  FakeAudio.last.play = () => Promise.reject(Object.assign(new Error('x'), { name: 'NotAllowedError' }))
  n.play(Q([card('B', 'b.mp3')], 'q2'))
  await tick()
  assert.equal(n.getSnapshot().status, 'paused')            // refused autoplay → waiting for a tap
  n.stop()
  assert.equal(n.getSnapshot().status, 'idle')
  assert.equal(n.getSnapshot().queueId, null)
})

test('works with no Audio, no speech and no Media Session at all (old browser)', () => {
  const n = new Narrator({ Audio: undefined, synth: null, Utterance: undefined, mediaSession: null, doc: null, storage: null })
  assert.equal(n.play(Q([card('A', 'a.mp3'), card('B', null)])), false)
  assert.equal(n.canPlayQueue(Q([card('A', 'a.mp3')])), false)
})
