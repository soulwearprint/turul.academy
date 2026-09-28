import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'

// „Hibát találtál?” — flags one content card for a reviewer (delayed quality control on
// top of the generators' guard rails). ctx: { topicId, lessonId, scope, mode }; index is
// the card's position in its content block. Offline, the service worker queues the POST.
const REASONS = ['teny', 'kviz', 'nyelv', 'erthetetlen', 'egyeb']
const MAX = 500

export default function ReportButton({ ctx, index, quiz = false, labelKey = 'report.cta' }) {
  const { session } = useAuth()
  const { t } = useLang()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState(null)
  const [comment, setComment] = useState('')
  const [state, setState] = useState(null)      // null | busy | done | queued | limit | error
  const [sent, setSent] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape' && state !== 'busy') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, state])

  useEffect(() => {
    if (state !== 'done' && state !== 'queued') return
    const id = setTimeout(() => { setOpen(false); setSent(true) }, 1800)
    return () => clearTimeout(id)
  }, [state])

  async function send() {
    setState('busy')
    try {
      await api.reports.create({
        topic_id: ctx.topicId, lesson_id: ctx.lessonId ?? null, scope: ctx.scope, mode: ctx.mode,
        card_index: index, reason, comment: comment.trim() || null,
      }, session?.access_token)
      setState('done')
    } catch (e) {
      if (String(e.message).includes('→ 429')) setState('limit')
      else if (!navigator.onLine) setState('queued')
      else setState('error')
    }
  }

  function openSheet() {
    setOpen(true); setReason(null); setComment(''); setState(null)
  }

  const reasons = REASONS.filter(r => quiz || r !== 'kviz')

  return (
    <>
      <button type="button" onClick={openSheet} disabled={sent}
        className="text-[11px] font-medium text-slate-400 hover:text-red-500 disabled:hover:text-slate-400 px-2 py-1">
        {sent ? t('report.sent.short') : `⚑ ${t(labelKey)}`}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 flex items-end sm:items-center justify-center"
          onClick={() => state !== 'busy' && setOpen(false)}>
          <div role="dialog" aria-modal="true" aria-label={t('report.title')}
            className="w-full max-w-lg bg-white rounded-t-3xl sm:rounded-3xl p-5 pb-8 animate-fade-up"
            onClick={e => e.stopPropagation()}>
            {state === 'done' || state === 'queued' ? (
              <p className="text-center text-emerald-700 font-semibold py-6">
                {state === 'done' ? t('report.thanks') : t('report.queued')}
              </p>
            ) : (
              <>
                <h2 className="font-bold text-slate-900 text-lg">{t('report.title')}</h2>
                <div className="flex flex-col gap-2 mt-4">
                  {reasons.map(r => (
                    <button key={r} type="button" onClick={() => setReason(r)}
                      className={`text-left px-4 py-3 rounded-xl border text-sm font-medium transition ${
                        reason === r ? 'border-turul-blue bg-brand-50 text-turul-blue' : 'border-slate-200 text-slate-700 hover:bg-slate-50'}`}>
                      {t(`report.reason.${r}`)}
                    </button>
                  ))}
                </div>
                <textarea value={comment} onChange={e => setComment(e.target.value.slice(0, MAX))} rows={3}
                  placeholder={t('report.comment.ph')}
                  className="mt-3 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:border-turul-blue" />
                <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                  <span>{t('report.privacy')}</span><span>{comment.length}/{MAX}</span>
                </div>
                {state === 'limit' && <p className="text-xs text-amber-600 mt-2">{t('report.limit')}</p>}
                {state === 'error' && <p className="text-xs text-red-500 mt-2">{t('report.error')}</p>}
                <div className="flex gap-2 mt-4">
                  <button type="button" onClick={() => setOpen(false)}
                    className="flex-1 py-3 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100">{t('common.cancel')}</button>
                  <button type="button" onClick={send} disabled={!reason || state === 'busy'}
                    className="flex-1 py-3 rounded-xl text-sm font-semibold text-white bg-turul-blue disabled:opacity-40">
                    {state === 'busy' ? '…' : t('report.send')}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
