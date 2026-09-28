import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'

// Reviewer queue for „Hibát találtál?” reports (role reviewer/admin — enforced by the API).
// One entry per reported card: reasons, students' comments, the card as reported / as it is
// now, an in-place editor for its wording, and resolve / dismiss.
const STATUSES = ['open', 'resolved', 'dismissed']
const SKIP = new Set(['type', 'anchor', 'question_type'])

// Field label from i18n (field.<key>), falling back to the raw key for unusual card fields.
function label(t, k) {
  const l = t(`field.${k}`)
  return l === `field.${k}` ? k : l
}

function textFields(card) {
  return Object.entries(card || {}).filter(([k, v]) => !SKIP.has(k) && (typeof v === 'string' || Array.isArray(v)))
}

function CardView({ card, t }) {
  return (
    <dl className="flex flex-col gap-2">
      {textFields(card).filter(([, v]) => (Array.isArray(v) ? v.length : v)).map(([k, v]) => (
        <div key={k}>
          <dt className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label(t, k)}</dt>
          <dd className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
            {Array.isArray(v) ? v.map((o, i) => <span key={i} className="block">{o}</span>) : v}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function CardEditor({ card, onSave, onCancel, t }) {
  const [draft, setDraft] = useState(card)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k, v) => setDraft(d => ({ ...d, [k]: v }))

  async function save() {
    setBusy(true); setError('')
    try { await onSave(draft) } catch { setError(t('queue.edit.error')) } finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col gap-3">
      {textFields(card).map(([k, v]) => (
        <label key={k} className="flex flex-col gap-1">
          <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label(t, k)}</span>
          {k === 'correct' ? (
            <select value={(draft[k] || '').trim().charAt(0).toUpperCase()} onChange={e => set(k, e.target.value)}
              className="input py-2 text-sm w-24">
              {['A', 'B', 'C', 'D'].map(l => <option key={l}>{l}</option>)}
            </select>
          ) : Array.isArray(v) ? (
            v.map((_, i) => (
              <input key={i} value={draft[k][i]} className="input py-2 text-sm"
                onChange={e => set(k, draft[k].map((o, j) => (j === i ? e.target.value : o)))} />
            ))
          ) : (
            <textarea value={draft[k]} onChange={e => set(k, e.target.value)} rows={v.length > 90 ? 4 : 2}
              className="input py-2 text-sm leading-relaxed" />
          )}
        </label>
      ))}
      {error && <p className="text-xs text-red-500">{error}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={onCancel} className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100">{t('common.cancel')}</button>
        <button type="button" onClick={save} disabled={busy}
          className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white bg-turul-blue disabled:opacity-50">{busy ? '…' : t('queue.edit.save')}</button>
      </div>
    </div>
  )
}

function Group({ g, status, token, t, onChanged }) {
  const [editing, setEditing] = useState(false)
  const [showSnapshot, setShowSnapshot] = useState(false)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const shown = g.current ?? g.snapshot
  const openTo = g.scope === 'lesson' ? `/nat/lessons/${g.lesson_id}${g.mode === 'quiz' ? '?tab=quiz' : ''}` : `/nat/topics/${g.topic_id}/quiz`

  async function act(next) {
    setBusy(true)
    try { await api.reports.resolve({ report_ids: g.report_ids, status: next, note }, token); onChanged() }
    finally { setBusy(false) }
  }

  async function saveEdit(card) {
    await api.reports.editCard({ block_id: g.block_id, card_index: g.card_index, card }, token)
    setEditing(false)
    onChanged()
  }

  return (
    <div className="card p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold text-slate-400 leading-snug">
            {g.topic_title} › {g.lesson_title ?? t('review.topic.quiz')}
          </p>
          <p className="text-xs font-bold text-slate-600 mt-0.5">{t(`queue.mode.${g.mode}`)} · #{g.card_index + 1}</p>
        </div>
        <Link to={openTo} className="shrink-0 text-xs font-semibold text-turul-blue">{t('queue.open')}</Link>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {Object.entries(g.reasons).map(([r, n]) => (
          <span key={r} className="text-[11px] font-semibold bg-red-50 text-red-600 rounded-full px-2 py-0.5">
            {t(`report.reason.${r}`)}{n > 1 ? ` ×${n}` : ''}
          </span>
        ))}
      </div>
      {g.comments.map((c, i) => (
        <p key={i} className="text-sm text-slate-600 italic border-l-2 border-slate-200 pl-3">„{c}”</p>
      ))}

      {g.changed && <p className="text-[11px] font-semibold text-amber-600">⚠ {t('queue.changed')}</p>}
      {!g.current && <p className="text-[11px] font-semibold text-amber-600">⚠ {t('queue.gone')}</p>}

      <div className="rounded-xl bg-slate-50 border border-slate-100 p-3">
        {editing
          ? <CardEditor card={g.current} onSave={saveEdit} onCancel={() => setEditing(false)} t={t} />
          : <CardView card={shown} t={t} />}
      </div>
      {g.changed && (
        <button type="button" onClick={() => setShowSnapshot(s => !s)} className="self-start text-xs font-semibold text-slate-500">
          {showSnapshot ? '▾' : '▸'} {t('queue.snapshot')}
        </button>
      )}
      {showSnapshot && <div className="rounded-xl border border-dashed border-slate-200 p-3"><CardView card={g.snapshot} t={t} /></div>}

      {status === 'open' ? (
        <div className="flex flex-col gap-2 border-t border-slate-100 pt-3">
          {!editing && g.editable && (
            <button type="button" onClick={() => setEditing(true)}
              className="py-2.5 rounded-xl text-sm font-semibold text-turul-blue bg-brand-50">✏️ {t('queue.edit')}</button>
          )}
          <input value={note} onChange={e => setNote(e.target.value)} placeholder={t('queue.note.ph')} className="input py-2 text-sm" />
          <div className="flex gap-2">
            <button type="button" disabled={busy} onClick={() => act('dismissed')}
              className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100 disabled:opacity-50">{t('queue.dismiss')}</button>
            <button type="button" disabled={busy} onClick={() => act('resolved')}
              className="flex-1 py-2.5 rounded-xl text-sm font-semibold text-white bg-emerald-600 disabled:opacity-50">✓ {t('queue.resolve')}</button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between gap-2 border-t border-slate-100 pt-3">
          <p className="text-xs text-slate-500">{g.reviewer_note || '—'}</p>
          <button type="button" disabled={busy} onClick={() => act('open')}
            className="shrink-0 text-xs font-semibold text-turul-blue">{t('queue.reopen')}</button>
        </div>
      )}
    </div>
  )
}

export default function ReportQueuePage() {
  const { session } = useAuth()
  const { t } = useLang()
  const token = session?.access_token
  const [status, setStatus] = useState('open')
  const [data, setData] = useState(null)
  const [forbidden, setForbidden] = useState(false)

  const load = useCallback(() => {
    api.reports.list(status, token)
      .then(d => { setData(d); setForbidden(false) })
      .catch(e => { if (String(e.message).includes('→ 403')) setForbidden(true); setData({ groups: [] }) })
  }, [status, token])

  useEffect(() => { setData(null); load() }, [load])

  return (
    <div className="pb-24">
      <PageHeader title={`🛠 ${t('queue.title')}`} backTo="/profile" />
      <div className="max-w-2xl mx-auto px-4 py-5 flex flex-col gap-4">
        {forbidden ? (
          <p className="card p-5 text-center text-slate-500">{t('queue.forbidden')}</p>
        ) : (
          <>
            <div className="flex gap-2">
              {STATUSES.map(s => (
                <button key={s} type="button" onClick={() => setStatus(s)}
                  className={`px-3.5 py-2 rounded-full text-sm font-semibold ${status === s ? 'bg-turul-blue text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {t(`queue.status.${s}`)}
                </button>
              ))}
            </div>
            {!data ? <p className="text-center text-slate-400">{t('common.loading')}</p>
              : data.groups.length === 0 ? <p className="card p-5 text-center text-slate-500">{t('queue.empty')}</p>
              : data.groups.map(g => (
                <Group key={`${g.block_id ?? g.lesson_id}-${g.mode}-${g.card_index}`} g={g} status={status} token={token} t={t} onChanged={load} />
              ))}
          </>
        )}
      </div>
    </div>
  )
}
