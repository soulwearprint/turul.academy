import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import BottomNav from '../components/BottomNav'
import TurulPortrait from '../components/TurulPortrait'
import { STAGES, stageForGrade, stageIndex } from '../lib/turul'

export default function TurulCompanionPage() {
  const { session, profile } = useAuth()
  const { t, lang } = useLang()
  const [progress, setProgress] = useState(null)

  const token = session?.access_token

  useEffect(() => {
    api.progress.me(token).then(setProgress).catch(() => {})
  }, [token])

  const xp = progress?.total_xp ?? 0
  const level = Math.floor(xp / 100) + 1
  const grade = profile?.grade ?? 7
  const stage = stageForGrade(grade)
  const sIdx = stageIndex(grade)

  return (
    <div className="pb-24">
      {/* Hero with the companion portrait */}
      <div className="hero-gradient px-5 pt-12 pb-10 rounded-b-3xl text-center">
        <p className="text-brand-100 text-xs font-semibold uppercase tracking-wide">{t('companion.stage')}</p>
        <h1 className="text-white text-2xl font-extrabold font-display mt-0.5">{stage.name[lang] ?? stage.name.hu}</h1>
        <div className="mx-auto mt-3 inline-flex items-center justify-center rounded-full bg-white shadow-lift ring-1 ring-black/5" style={{ width: 188, height: 188 }}>
          <TurulPortrait grade={grade} size={160} />
        </div>
        <div className="flex justify-center gap-2.5 mt-3">
          <div className="chip"><span className="text-amber-300">⭐</span> {xp} XP</div>
          <div className="chip">Lv {level}</div>
        </div>
      </div>

      <div className="px-4 -mt-4 max-w-lg mx-auto space-y-5">
        {/* Evolution journey */}
        <section className="card p-4">
          <h2 className="font-bold text-slate-800 mb-1">{t('companion.journey')}</h2>
          <p className="text-xs text-slate-400 mb-3">{t('companion.journey.sub')}</p>
          <div className="grid grid-cols-4 gap-1.5">
            {STAGES.map((s, i) => {
              const current = i === sIdx
              const reached = i <= sIdx
              return (
                <div
                  key={s.key}
                  className={`flex flex-col items-center rounded-xl py-3 px-1 transition-all ${
                    current ? 'bg-brand-50 ring-2 ring-turul-blue' : ''
                  }`}
                >
                  <TurulPortrait
                    stage={s.key}
                    size={current ? 64 : 52}
                    animate={false}
                    className={reached ? '' : 'opacity-30 grayscale'}
                  />
                  <span className={`text-[10px] font-semibold mt-1 text-center leading-tight ${current ? 'text-turul-blue' : reached ? 'text-slate-600' : 'text-slate-400'}`}>
                    {s.name[lang] ?? s.name.hu}
                  </span>
                  <span className="text-[9px] text-slate-400">{s.minGrade}–{s.maxGrade}.</span>
                </div>
              )
            })}
          </div>
        </section>

        {/* Customization teaser */}
        <section className="card p-5 text-center">
          <div className="text-3xl mb-1">🎨</div>
          <h2 className="font-bold text-slate-800">{t('companion.customize.title')}</h2>
          <p className="text-sm text-slate-500 mt-1 leading-relaxed">{t('companion.customize.soon')}</p>
        </section>
      </div>

      <BottomNav />
    </div>
  )
}
