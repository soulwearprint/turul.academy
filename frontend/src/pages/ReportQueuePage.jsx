import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import { mediaUrl } from '../lib/media'

// Reviewer queue for „Hibát találtál?” reports (role reviewer/admin — enforced by the API).
// One entry per reported card: reasons, students' comments, the card as reported / as it is
// now, an in-place editor for its wording, and resolve / dismiss. The „Szerkesztések” tab
// lists every card edit (before → after, who, when) with undo.
const STATUSES = ['open', 'resolved', 'dismissed']
const TABS = [...STATUSES, 'edits']
const SKIP = new Set(['type', 'anchor', 'question_type'])

// Field label from i18n (field.<key>), falling back to the raw key for unusual card fields.
function label(t, k) {
  const l = t(`field.${k}`)
  return l === `field.${k}` ? k : l
}

// Editable wording: strings, lists of strings (options) and lists of flat string records
// (a timeline's { when, what }). Pictures and sketches are shown, not edited, here.
const isRecord = x => x && typeof x === 'object' && !Array.isArray(x) && Object.values(x).every(v => typeof v === 'string')
function textFields(card) {
  return Object.entries(card || {}).filter(([k, v]) => !SKIP.has(k) && (typeof v === 'string'
    || (Array.isArray(v) && (v.every(x => typeof x === 'string') || v.every(isRecord)))))
}

function Thumb({ src, alt }) {
  const url = mediaUrl(src)
  return url ? <img src={url} alt={alt || ''} loading="lazy" className="max-h-40 w-auto rounded-lg border border-slate-200 bg-white" /> : null
}

function cardLink(c) {
  return c.scope === 'lesson' ? `/nat/lessons/${c.lesson_id}${c.mode === 'quiz' ? '?tab=quiz' : ''}` : `/nat/topics/${c.topic_id}/quiz`
}

const isConflict = e => String(e?.message).includes('→ 409')

function CardHeader({ c, t }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-slate-400 leading-snug">
          {c.topic_title} › {c.lesson_title ?? t('review.topic.quiz')}
        </p>
        <p className="text-xs font-bold text-slate-600 mt-0.5">{t(`queue.mode.${c.mode}`)} · #{c.card_index + 1}</p>
      </div>
      <Link to={cardLink(c)} className="shrink-0 text-xs font-semibold text-turul-blue">{t('queue.open')}</Link>
    </div>
  )
}

function CardView({ card, t }) {
  return (
    <dl className="flex flex-col gap-2">
      {card?.image?.src && <Thumb src={card.image.src} alt={card.image.alt} />}
      {textFields(card).filter(([, v]) => (Array.isArray(v) ? v.length : v)).map(([k, v]) => (
        <div key={k}>
          <dt className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label(t, k)}</dt>
          <dd className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
            {Array.isArray(v)
              ? v.map((o, i) => <span key={i} className="block">{typeof o === 'string' ? o : Object.values(o).join(' — ')}</span>)
              : v}
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
    try { await onSave(draft) }
    catch (e) { setError(t(isConflict(e) ? 'queue.edit.conflict' : 'queue.edit.error')) }
    finally { setBusy(false) }
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
          ) : Array.isArray(v) && v.every(isRecord) ? (
            v.map((item, i) => (
              <div key={i} className="flex flex-col gap-1 border-l-2 border-slate-200 pl-2">
                {Object.keys(item).map(f => (
                  <input key={f} value={draft[k][i][f]} aria-label={`${label(t, f)} ${i + 1}`} className="input py-1.5 text-sm"
                    onChange={e => set(k, draft[k].map((o, j) => (j === i ? { ...o, [f]: e.target.value } : o)))} />
                ))}
              </div>
            ))
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

  async function act(next) {
    setBusy(true)
    try { await api.reports.resolve({ report_ids: g.report_ids, status: next, note }, token); onChanged() }
    finally { setBusy(false) }
  }

  async function saveEdit(card) {
    // `before` = the card as loaded: the API refuses (409) if someone changed it meanwhile.
    await api.reports.editCard({ block_id: g.block_id, card_index: g.card_index, card,
                                 before: g.current, report_ids: g.report_ids }, token)
    setEditing(false)
    onChanged()
  }

  return (
    <div className="card p-4 flex flex-col gap-3">
      <CardHeader c={g} t={t} />

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

// Every string leaf an edit touched (options line by line, timeline items, image fields…).
function leaves(v, path = []) {
  if (typeof v === 'string') return [[path, v]]
  if (Array.isArray(v)) return v.flatMap((x, i) => leaves(x, [...path, i]))
  if (v && typeof v === 'object') return Object.entries(v).flatMap(([k, x]) => leaves(x, [...path, k]))
  return []
}

function fieldDiffs(before, after) {
  const b = new Map(leaves(before).filter(([p]) => !SKIP.has(p[0])).map(([p, v]) => [p.join('.'), [p, v]]))
  const a = new Map(leaves(after).filter(([p]) => !SKIP.has(p[0])).map(([p, v]) => [p.join('.'), [p, v]]))
  return [...new Set([...b.keys(), ...a.keys()])]
    .filter(id => b.get(id)?.[1] !== a.get(id)?.[1])
    .map(id => ({ id, path: (b.get(id) ?? a.get(id))[0], before: b.get(id)?.[1] ?? '', after: a.get(id)?.[1] ?? '' }))
}

function pathLabel(t, path) {
  return path.map(p => (typeof p === 'number' ? `${p + 1}.` : label(t, p))).join(' · ')
}

function EditEntry({ e, token, t, lang, onChanged }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const when = new Date(e.created_at).toLocaleString(lang === 'hu' ? 'hu-HU' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short' })

  async function undo() {
    setBusy(true); setError('')
    try { await api.reports.revert(e.id, token); onChanged() }
    catch (err) { setError(t(isConflict(err) ? 'queue.edits.conflict' : 'queue.edits.error')) }
    finally { setBusy(false) }
  }

  return (
    <div className="card p-4 flex flex-col gap-3">
      <CardHeader c={e} t={t} />
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
        <span>{e.editor ?? t('queue.edits.system')} · {when}</span>
        {e.is_undo && <span className="font-semibold bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">↩ {t('queue.edits.badge.undo')}</span>}
        {e.reverted && <span className="font-semibold bg-amber-50 text-amber-700 rounded-full px-2 py-0.5">{t('queue.edits.badge.reverted')}</span>}
      </div>

      <div className="flex flex-col gap-2.5">
        {fieldDiffs(e.before, e.after).map(d => (
          <div key={d.id}>
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{pathLabel(t, d.path)}</p>
            {d.path[0] === 'image' && d.path[1] === 'src' ? (
              <div className="flex items-center gap-2 mt-1">
                {d.before ? <Thumb src={d.before} /> : <span className="text-xs text-slate-400">—</span>}
                <span className="text-slate-400">→</span>
                {d.after ? <Thumb src={d.after} /> : <span className="text-xs text-slate-400">—</span>}
              </div>
            ) : (
              <>
                {d.before && <p className="text-sm leading-relaxed rounded-lg px-2.5 py-1.5 mt-1 bg-red-50 text-red-700 line-through decoration-red-300 whitespace-pre-line">{d.before}</p>}
                {d.after && <p className="text-sm leading-relaxed rounded-lg px-2.5 py-1.5 mt-1 bg-emerald-50 text-emerald-800 whitespace-pre-line">{d.after}</p>}
              </>
            )}
          </div>
        ))}
      </div>

      {!e.block_id && <p className="text-[11px] font-semibold text-amber-600">⚠ {t('queue.edits.gone')}</p>}
      {error && <p className="text-xs text-red-500">{error}</p>}
      {e.undoable && (
        <button type="button" onClick={undo} disabled={busy}
          className="self-start px-3.5 py-2 rounded-xl text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:opacity-50">
          {busy ? '…' : `↩ ${t('queue.edits.undo')}`}
        </button>
      )}
    </div>
  )
}

export default function ReportQueuePage() {
  const { session } = useAuth()
  const { t, lang } = useLang()
  const token = session?.access_token
  const [tab, setTab] = useState('open')
  const [data, setData] = useState(null)
  const [forbidden, setForbidden] = useState(false)
  const [version, setVersion] = useState(0)          // bump → reload the current tab
  const reload = () => setVersion(v => v + 1)

  useEffect(() => {
    let stale = false                                  // ignore a slow response for a tab we left
    const req = tab === 'edits' ? api.reports.edits(token) : api.reports.list(tab, token)
    req.then(d => { if (!stale) { setData(d); setForbidden(false) } })
      .catch(e => { if (stale) return; if (String(e.message).includes('→ 403')) setForbidden(true); setData({}) })
    return () => { stale = true }
  }, [tab, token, version])

  function pick(next) {
    if (next !== tab) { setData(null); setTab(next) }
  }

  const items = tab === 'edits' ? data?.edits : data?.groups

  return (
    <div className="pb-24">
      <PageHeader title={`🛠 ${t('queue.title')}`} backTo="/profile" />
      <div className="max-w-2xl mx-auto px-4 py-5 flex flex-col gap-4">
        {forbidden ? (
          <p className="card p-5 text-center text-slate-500">{t('queue.forbidden')}</p>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              {TABS.map(s => (
                <button key={s} type="button" onClick={() => pick(s)}
                  className={`px-3.5 py-2 rounded-full text-sm font-semibold ${tab === s ? 'bg-turul-blue text-white' : 'bg-slate-100 text-slate-600'}`}>
                  {t(`queue.status.${s}`)}
                </button>
              ))}
            </div>
            {tab === 'edits' && <p className="text-xs text-slate-500">{t('queue.edits.hint')}</p>}
            {!data ? <p className="text-center text-slate-400">{t('common.loading')}</p>
              : !items?.length ? <p className="card p-5 text-center text-slate-500">{t(tab === 'edits' ? 'queue.edits.empty' : 'queue.empty')}</p>
              : tab === 'edits' ? items.map(e => <EditEntry key={e.id} e={e} token={token} t={t} lang={lang} onChanged={reload} />)
              : items.map(g => (
                <Group key={`${g.block_id ?? g.lesson_id}-${g.mode}-${g.card_index}`} g={g} status={tab} token={token} t={t} onChanged={reload} />
              ))}
          </>
        )}
      </div>
    </div>
  )
}
