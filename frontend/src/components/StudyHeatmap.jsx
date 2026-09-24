import { useMemo, useState } from 'react'
import { fmtDuration } from '../lib/badges'

// GitHub-style study calendar: one column per week (Mon→Sun, the Hungarian week),
// cell shade = minutes studied that day. Dates are the server's Budapest-local day
// strings, walked in UTC so the device timezone can't shift a cell.
export const WEEKS = 17
const DAY_MS = 86_400_000
const LEVEL_CLS = ['bg-slate-100', 'bg-brand-200', 'bg-brand-400', 'bg-brand-600', 'bg-brand-800']

function level(day) {
  if (!day) return 0
  const min = day.seconds / 60
  if (min <= 0) return day.xp > 0 || day.lessons > 0 ? 1 : 0   // quiz-only day (before time tracking)
  if (min < 5) return 1
  if (min < 15) return 2
  if (min < 30) return 3
  return 4
}

const iso = (ms) => new Date(ms).toISOString().slice(0, 10)

export default function StudyHeatmap({ data, t, lang }) {
  const [picked, setPicked] = useState(null)
  const locale = lang === 'en' ? 'en-GB' : 'hu-HU'

  const { weeks, months } = useMemo(() => {
    const byDate = Object.fromEntries((data?.days ?? []).map(d => [d.date, d]))
    const todayMs = Date.parse(`${data?.today ?? iso(Date.now())}T00:00:00Z`)
    const weekday = (new Date(todayMs).getUTCDay() + 6) % 7          // 0 = Monday
    const startMs = todayMs - (weekday + (WEEKS - 1) * 7) * DAY_MS
    const monthFmt = new Intl.DateTimeFormat(locale, { month: 'short', timeZone: 'UTC' })
    const weeks = []
    const months = []
    for (let w = 0; w < WEEKS; w++) {
      const col = []
      for (let d = 0; d < 7; d++) {
        const ms = startMs + (w * 7 + d) * DAY_MS
        const date = iso(ms)
        col.push(ms > todayMs ? null : { date, ms, day: byDate[date], isToday: ms === todayMs })
      }
      const firstOfMonth = col.find(c => c && c.date.endsWith('-01'))
      if (w === 0 || firstOfMonth) {
        months.push({ w, label: monthFmt.format(new Date((firstOfMonth ?? col[0]).ms)).replace('.', '') })
      }
      weeks.push(col)
    }
    // The leading partial month's label would collide with the next month's.
    if (months.length > 1 && months[1].w - months[0].w < 3) months.shift()
    return { weeks, months }
  }, [data, locale])

  const activeDays = (data?.days ?? []).filter(d => level(d) > 0).length
  const dayLabels = lang === 'en' ? ['Mon', '', 'Wed', '', 'Fri', '', ''] : ['H', '', 'Sze', '', 'P', '', '']
  const pickedFmt = new Intl.DateTimeFormat(locale, { month: 'long', day: 'numeric', weekday: 'short', timeZone: 'UTC' })

  return (
    <div className="card p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-bold text-slate-800">{t('progress.calendar.title')}</h2>
        <span className="text-xs text-slate-400">{t('progress.calendar.sub', { n: WEEKS })}</span>
      </div>

      <div className="grid gap-[3px]" style={{ gridTemplateColumns: `1.6rem repeat(${WEEKS}, minmax(0, 1fr))` }}>
        {/* month labels */}
        <div />
        {weeks.map((_, w) => {
          const m = months.find(x => x.w === w)
          return <div key={`m${w}`} className="text-[10px] text-slate-400 leading-3 h-3 whitespace-nowrap overflow-visible">{m?.label ?? ''}</div>
        })}
        {/* 7 rows: weekday label + one cell per week */}
        {Array.from({ length: 7 }).flatMap((_, d) => [
          <div key={`l${d}`} className="text-[10px] text-slate-400 leading-none self-center">{dayLabels[d]}</div>,
          ...weeks.map((col, w) => {
            const c = col[d]
            if (!c) return <div key={`${w}-${d}`} />
            const lv = level(c.day)
            return (
              <button key={`${w}-${d}`} type="button" onClick={() => setPicked(c)}
                aria-label={c.date}
                className={`aspect-square rounded-[3px] ${LEVEL_CLS[lv]} ${c.isToday ? 'ring-1 ring-offset-1 ring-turul-blue' : ''} ${picked?.date === c.date ? 'outline outline-2 outline-slate-700' : ''}`} />
            )
          }),
        ])}
      </div>

      <div className="flex justify-end items-center gap-1 mt-2 text-[10px] text-slate-400">
        {t('progress.calendar.less')}
        {LEVEL_CLS.map(c => <span key={c} className={`w-2.5 h-2.5 rounded-[2px] ${c}`} />)}
        {t('progress.calendar.more')}
      </div>
      <p className="mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
        {picked
          ? <><span className="font-semibold text-slate-700">{pickedFmt.format(new Date(picked.ms))}</span>{' · '}
              {level(picked.day) > 0
                ? t('progress.calendar.day', { time: fmtDuration(picked.day.seconds, lang), xp: picked.day.xp })
                : t('progress.calendar.rest')}</>
          : <>{t('progress.calendar.active', { n: activeDays })} · {t('progress.calendar.longest', { n: data?.longest_streak ?? 0 })}</>}
      </p>
    </div>
  )
}
