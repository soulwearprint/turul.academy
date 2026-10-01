import { useEffect, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import { CardList, DeepDive, QuizRunner } from '../components/ContentCards'
import PageHeader from '../components/PageHeader'
import ReportButton from '../components/ReportButton'
import ReadAloudButton from '../components/ReadAloudButton'
import { natTitle } from '../lib/nat'
import { useStudyTimer } from '../lib/useStudyTimer'

const MODE_EMOJI = { text: '📖', story: '🎭', visual: '🗺️', quiz: '🧠' }
const MAIN_MODES = ['text', 'story', 'visual', 'quiz']

// On-demand collapsible layer beyond the main tabs — a lesson has at most one of these.
const EXTRA_LAYERS = {
  world:      { key: 'nat.layer.world' },
  experiment: { key: 'nat.layer.experiment' },
}

export default function NatLessonPage() {
  const { lessonId } = useParams()
  const [searchParams] = useSearchParams()
  const { session } = useAuth()
  const token = session?.access_token
  const { t, lang } = useLang()
  const [lesson, setLesson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [mode, setMode] = useState('text')
  const [showExtra, setShowExtra] = useState(false)
  const [viewedTabs, setViewedTabs] = useState(new Set())
  const [openDeep, setOpenDeep] = useState(null)       // anchor of the open „Mesélj még!” panel
  const readSent = useRef(false)
  const activeTabRef = useRef(null)

  // Keep the active tab visible in the scrollable strip (e.g. "Kvíz" opened via ?tab=quiz).
  useEffect(() => {
    activeTabRef.current?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }, [mode, lesson])

  // Time counts toward whatever the student is reading: an open „Mesélj még!” panel, else
  // the open extra layer, else the tab.
  const timedMode = openDeep !== null && mode === 'text' ? 'deep'
    : showExtra && lesson ? Object.keys(EXTRA_LAYERS).find(m => lesson.blocks[m]) ?? mode : mode
  const { engaged } = useStudyTimer({
    mode: timedMode,
    enabled: !!lesson,
    onFlush: (delta) => api.nat.trackTime(lessonId, delta, token).catch(() => {}),
  })

  useEffect(() => {
    api.nat.lesson(lessonId).then(l => {
      setLesson(l)
      const wanted = searchParams.get('tab')
      const firstMode = (wanted && l.blocks[wanted] && MAIN_MODES.includes(wanted))
        ? wanted : (l.modes.find(m => MAIN_MODES.includes(m)) || 'text')
      setMode(firstMode)
      setViewedTabs(new Set([firstMode]))
    }).finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lessonId])

  // "All cards read" = every non-quiz tab opened at least once (the quiz is a separate,
  // higher status — completing it is what actually moves a Téma to "completed").
  // Only once the visit is past the mis-tap threshold, so a stray open marks nothing.
  useEffect(() => {
    if (!lesson || !engaged || readSent.current) return
    const readable = MAIN_MODES.filter(m => m !== 'quiz' && lesson.blocks[m])
    if (readable.length > 0 && readable.every(m => viewedTabs.has(m))) {
      readSent.current = true
      api.nat.setProgress(lessonId, { status: 'read' }, token).catch(() => {})
    }
  }, [lesson, engaged, viewedTabs, lessonId, token])

  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>
  if (!lesson) return <div className="flex h-screen items-center justify-center text-slate-400">{t('nat.not.found')}</div>

  const tabs = MAIN_MODES.filter(m => lesson.blocks[m])
  const extraMode = Object.keys(EXTRA_LAYERS).find(m => lesson.blocks[m])

  // Deep dives are anchored to text cards by index (one per card at most); keep each one's own
  // position in the deep block too — that's the index a report refers to.
  const deepByAnchor = Object.fromEntries((lesson.blocks.deep || []).map((d, i) => [d.anchor, { card: d, index: i }]))
  const reportCtx = { topicId: lesson.topic_id, lessonId, scope: 'lesson' }

  // „Felolvasás”: one queue per tab/layer, index-aligned with its cards (the API builds the text).
  const title = natTitle(lesson, lang)
  const queueFor = (m) => (lesson.narration?.[m] ? { id: `${lessonId}:${m}`, title, items: lesson.narration[m] } : null)

  function openTab(m) {
    setMode(m)
    setOpenDeep(null)
    if (!viewedTabs.has(m)) setViewedTabs(new Set(viewedTabs).add(m))
  }

  return (
    <div className="pb-24">
      <PageHeader title={title} backTo={-1} />

      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* Mode tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
          {tabs.map(m => (
            <button key={m} onClick={() => openTab(m)} ref={mode === m ? activeTabRef : null}
              className={`whitespace-nowrap px-3.5 py-2 rounded-full text-sm font-semibold transition ${
                mode === m ? 'bg-turul-blue text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
              {MODE_EMOJI[m]} {t(`mode.${m}`)}
            </button>
          ))}
        </div>

        {mode !== 'quiz' && queueFor(mode) && (
          <div className="mb-4"><ReadAloudButton variant="lesson" queue={queueFor(mode)} /></div>
        )}

        {mode === 'quiz' ? (
          <QuizRunner
            cards={lesson.blocks.quiz}
            narration={queueFor('quiz')}
            reportCtx={{ ...reportCtx, mode: 'quiz' }}
            onSubmit={(answers) => api.nat.submitQuiz(
              { topic_id: lesson.topic_id, lesson_id: lessonId, scope: 'lesson', answers }, token)}
          />
        ) : (
          <CardList mode={mode} cards={lesson.blocks[mode]} reportCtx={reportCtx} narration={queueFor(mode)}
            renderAfter={mode === 'text' ? (i) => deepByAnchor[i] && (
              <DeepDive card={deepByAnchor[i].card} open={openDeep === i}
                onToggle={() => setOpenDeep(o => (o === i ? null : i))}
                listen={<ReadAloudButton queue={{ id: `${lessonId}:deep:${deepByAnchor[i].index}`, title,
                  items: [lesson.narration?.deep?.[deepByAnchor[i].index] ?? null] }} />}
                footer={<ReportButton ctx={{ ...reportCtx, mode: 'deep' }} index={deepByAnchor[i].index} labelKey="report.cta.deep" />} />
            ) : undefined} />
        )}

        {/* On-demand extra layer (world for History, experiment for Physics) */}
        {extraMode && (
          <div className="mt-6">
            <button onClick={() => setShowExtra(s => !s)}
              className="w-full flex items-center justify-between bg-slate-900 text-white rounded-xl px-4 py-3 font-semibold">
              <span>{t(EXTRA_LAYERS[extraMode].key)}</span>
              <span className="text-white/60">{showExtra ? '▲' : '▼'}</span>
            </button>
            {showExtra && <div className="mt-3"><CardList mode={extraMode} cards={lesson.blocks[extraMode]} reportCtx={reportCtx} narration={queueFor(extraMode)} /></div>}
          </div>
        )}
      </div>
    </div>
  )
}
