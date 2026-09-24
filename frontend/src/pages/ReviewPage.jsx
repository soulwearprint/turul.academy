import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import { natTitle } from '../lib/nat'
import PageHeader from '../components/PageHeader'

// "Questions you keep missing": every question answered wrong on the latest attempt of
// its quiz, most-missed first. Practising here is local only (no XP) — a question leaves
// the list once the student gets it right in the real quiz, which the retake link opens.
export default function ReviewPage() {
  const { session } = useAuth()
  const { t, lang } = useLang()
  const [data, setData] = useState(null)

  useEffect(() => {
    api.nat.review(session?.access_token).then(setData).catch(() => setData({ items: [], count: 0 }))
  }, [session?.access_token])

  if (!data) return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>

  return (
    <div className="pb-24">
      <PageHeader title={`🔁 ${t('review.title')}`} subtitle={data.count ? t('review.teaser', { n: data.count }) : null} backTo="/progress" />
      <div className="max-w-2xl mx-auto px-4 py-5 flex flex-col gap-4">
        {data.items.length === 0 ? (
          <p className="card p-5 text-center text-slate-500">{t('review.empty')}</p>
        ) : (
          <>
            <p className="text-sm text-slate-500">{t('review.hint')}</p>
            {data.items.map(q => <ReviewCard key={`${q.scope}-${q.lesson_id ?? q.topic_id}-${q.index}`} q={q} t={t} lang={lang} />)}
          </>
        )}
      </div>
    </div>
  )
}

function ReviewCard({ q, t, lang }) {
  const [picked, setPicked] = useState(null)
  const where = q.scope === 'lesson'
    ? `${natTitle({ title: q.topic_title, title_hu: q.topic_title_hu }, lang)} › ${natTitle({ title: q.lesson_title, title_hu: q.lesson_title_hu }, lang)}`
    : `${natTitle({ title: q.topic_title, title_hu: q.topic_title_hu }, lang)} › ${t('review.topic.quiz')}`
  const retakeTo = q.scope === 'lesson' ? `/nat/lessons/${q.lesson_id}?tab=quiz` : `/nat/topics/${q.topic_id}/quiz`

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-100 px-5 py-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-semibold text-slate-400 leading-snug">{where}</p>
        <span className="shrink-0 text-[11px] font-bold text-red-500 bg-red-50 rounded-full px-2 py-0.5">{t('review.missed', { n: q.misses })}</span>
      </div>
      <h3 className="text-base font-bold text-slate-900 leading-snug">{q.question}</h3>
      <div className="flex flex-col gap-2">
        {q.options.map((opt, i) => {
          const letter = String.fromCharCode(65 + i)
          let cls = 'border-slate-200 bg-white hover:bg-slate-50'
          if (picked) {
            if (letter === q.correct) cls = 'border-emerald-500 bg-emerald-50'
            else if (letter === picked) cls = 'border-red-400 bg-red-50'
            else cls = 'border-slate-200 bg-white opacity-60'
          }
          return (
            <button key={i} type="button" disabled={!!picked} onClick={() => setPicked(letter)}
              className={`text-left px-4 py-3 rounded-xl border text-sm font-medium text-slate-700 transition ${cls}`}>
              {opt}
            </button>
          )
        })}
      </div>
      {picked && q.explanation && (
        <p className="text-sm text-slate-600 bg-slate-50 rounded-xl px-4 py-3">
          {picked === q.correct ? '✅ ' : '❌ '}{q.explanation}
        </p>
      )}
      {picked && (
        <Link to={retakeTo} className="self-end text-sm font-semibold text-turul-blue">{t('review.retake')}</Link>
      )}
    </div>
  )
}
