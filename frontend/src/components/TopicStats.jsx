import { useState } from 'react'
import { natTitle } from '../lib/nat'
import { fmtDuration } from '../lib/badges'

// Per-Témakör bars: time per card read (blue, scaled to the slowest topic) against the
// quiz score (green = latest attempt, dark tick = first attempt) — so "slow + low"
// topics stand out. Tap a topic for its Témák, each with a reset for skewed data.
const STATUS_DOT = { in_progress: 'bg-amber-400', read: 'bg-sky-400', completed: 'bg-emerald-500' }

function Bar({ pct, tick, cls }) {
  return (
    <div className="relative flex-1 h-2.5 bg-slate-100 rounded-full">
      <div className={`h-full rounded-full ${cls}`} style={{ width: `${Math.max(pct, pct > 0 ? 3 : 0)}%` }} />
      {tick != null && (
        <div className="absolute -top-0.5 -bottom-0.5 w-[3px] rounded bg-slate-700" style={{ left: `calc(${tick}% - 1.5px)` }} />
      )}
    </div>
  )
}

function quizLabel(first, latest) {
  if (latest == null) return null
  return first != null && first !== latest ? `${first}% → ${latest}%` : `${latest}%`
}

export default function TopicStats({ topics, t, lang, onResetLesson }) {
  const [open, setOpen] = useState(null)
  const [confirming, setConfirming] = useState(null)
  const [busy, setBusy] = useState(false)
  const maxSpc = Math.max(1, ...topics.map(x => x.sec_per_card || 0))

  async function reset(lessonId) {
    setBusy(true)
    try { await onResetLesson(lessonId) } finally { setBusy(false); setConfirming(null) }
  }

  return (
    <section>
      <h2 className="font-bold text-slate-800 mb-1">{t('progress.topics.title')}</h2>
      <div className="flex items-center gap-4 text-[11px] text-slate-500 mb-3">
        <span className="flex items-center gap-1"><span className="w-3 h-2 rounded-full bg-brand-500" />{t('progress.legend.time')}</span>
        <span className="flex items-center gap-1"><span className="w-3 h-2 rounded-full bg-emerald-500" />{t('progress.legend.quiz')}</span>
        <span className="flex items-center gap-1"><span className="w-[3px] h-3 rounded bg-slate-700" />{t('progress.legend.first')}</span>
      </div>

      <div className="space-y-2.5">
        {topics.map(tp => {
          const expanded = open === tp.topic_id
          return (
            <div key={tp.topic_id} className="card overflow-hidden">
              <button type="button" onClick={() => setOpen(expanded ? null : tp.topic_id)} className="w-full text-left p-4">
                <div className="flex items-center gap-2 mb-2.5">
                  <span className="font-semibold text-sm text-slate-800 flex-1 min-w-0 truncate">{natTitle(tp, lang)}</span>
                  <span className="text-[11px] text-slate-400 shrink-0">{tp.grade}{t('common.grade')} · {tp.lessons_done}/{tp.lessons_total}</span>
                  <span className={`text-slate-400 transition-transform ${expanded ? 'rotate-90' : ''}`}>›</span>
                </div>
                <div className="flex items-center gap-2">
                  <Bar pct={((tp.sec_per_card || 0) / maxSpc) * 100} cls="bg-brand-500" />
                  <span className="w-24 text-right text-xs font-semibold text-brand-700 shrink-0">
                    {tp.sec_per_card != null ? t('progress.per.card', { time: fmtDuration(tp.sec_per_card, lang) }) : '—'}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <Bar pct={tp.quiz_avg ?? 0} tick={tp.first_avg != null && tp.quiz_avg != null && tp.first_avg !== tp.quiz_avg ? tp.first_avg : null} cls="bg-emerald-500" />
                  <span className="w-24 text-right text-xs font-semibold text-emerald-700 shrink-0">
                    {quizLabel(tp.first_avg, tp.quiz_avg) ?? <span className="font-normal text-slate-400">{t('progress.no.quiz')}</span>}
                  </span>
                </div>
              </button>

              {expanded && (
                <div className="border-t border-slate-100 bg-slate-50/60 px-4 py-2 divide-y divide-slate-100">
                  {tp.topic_quiz != null && (
                    <p className="py-2 text-xs font-semibold text-slate-600">🎯 {t('progress.topic.quiz', { n: tp.topic_quiz })}</p>
                  )}
                  {tp.lessons.map(l => (
                    <div key={l.lesson_id} className="py-2.5">
                      <div className="flex items-start gap-2">
                        <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[l.status] ?? 'bg-slate-300'}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-800 leading-snug">{natTitle(l, lang)}</p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            ⏱ {fmtDuration(l.seconds, lang)}
                            {l.sec_per_card != null && <> · {t('progress.per.card', { time: fmtDuration(l.sec_per_card, lang) })}</>}
                            {' · '}🎯 {quizLabel(l.first_score, l.quiz_score) ?? t('progress.no.quiz')}
                            {l.attempts > 1 && <> ({t('progress.attempts', { n: l.attempts })})</>}
                          </p>
                        </div>
                        {confirming !== l.lesson_id && (
                          <button type="button" onClick={() => setConfirming(l.lesson_id)}
                            className="shrink-0 text-xs font-semibold text-slate-400 hover:text-red-500 px-1.5 py-1">
                            {t('progress.reset.lesson')}
                          </button>
                        )}
                      </div>
                      {confirming === l.lesson_id && (
                        <div className="mt-2 ml-4 rounded-xl bg-white border border-red-100 p-3">
                          <p className="text-xs text-slate-600">{t('progress.reset.lesson.confirm')}</p>
                          <div className="flex gap-2 mt-2">
                            <button type="button" onClick={() => setConfirming(null)}
                              className="flex-1 py-2 rounded-lg text-xs font-semibold text-slate-600 bg-slate-100">{t('common.cancel')}</button>
                            <button type="button" disabled={busy} onClick={() => reset(l.lesson_id)}
                              className="flex-1 py-2 rounded-lg text-xs font-semibold text-red-600 bg-red-50 disabled:opacity-50">
                              {busy ? '…' : t('progress.reset.lesson.cta')}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
