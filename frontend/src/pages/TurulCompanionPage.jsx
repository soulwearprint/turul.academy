import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import BottomNav from '../components/BottomNav'
import TurulMascot from '../components/TurulMascot'
import {
  COLOR_OPTIONS, ACCESSORY_OPTIONS, STAGES,
  stageForGrade, stageIndex, getTurulConfig, setTurulConfig,
} from '../lib/turul'

const COLOR_SWATCH = { blue: '#2563EB', green: '#22C55E', purple: '#8B5CF6', gold: '#F59E0B' }
const ACCESSORY_LABEL = {
  none:       { hu: 'Semmi',      en: 'None' },
  glasses:    { hu: 'Szemüveg',   en: 'Glasses' },
  headphones: { hu: 'Fejhallgató', en: 'Headphones' },
  cap:        { hu: 'Kalap',      en: 'Cap' },
}

export default function TurulCompanionPage() {
  const { session, profile } = useAuth()
  const { t, lang } = useLang()
  const [config, setConfig] = useState(getTurulConfig())
  const [progress, setProgress] = useState(null)

  const token = session?.access_token

  useEffect(() => {
    api.progress.me(token).then(setProgress).catch(() => {})
  }, [token])

  function update(patch) {
    setConfig(setTurulConfig(patch))
  }

  const xp = progress?.total_xp ?? 0
  const level = Math.floor(xp / 100) + 1
  const grade = profile?.grade ?? 7
  const stage = stageForGrade(grade)
  const sIdx = stageIndex(grade)

  return (
    <div className="pb-24">
      {/* Hero with the companion */}
      <div className="hero-gradient px-5 pt-12 pb-10 rounded-b-3xl text-center">
        <p className="text-brand-100 text-xs font-semibold uppercase tracking-wide">{t('companion.stage')}</p>
        <h1 className="text-white text-2xl font-extrabold font-display mt-0.5">{stage.name[lang] ?? stage.name.hu}</h1>
        <div className="mx-auto mt-3 inline-flex items-center justify-center rounded-full bg-white shadow-lift ring-1 ring-black/5" style={{ width: 188, height: 188 }}>
          <TurulMascot mood="happy" color={config.color} accessory={config.accessory} size={158} shadow={false} />
        </div>
        <div className="flex justify-center gap-2.5 mt-2">
          <div className="chip"><span className="text-amber-300">⭐</span> {xp} XP</div>
          <div className="chip">Lv {level}</div>
        </div>
      </div>

      <div className="px-4 -mt-4 max-w-lg mx-auto space-y-5">
        {/* Evolution journey */}
        <section className="card p-4">
          <h2 className="font-bold text-slate-800 mb-3">{t('companion.journey')}</h2>
          <div className="flex items-center justify-between gap-1">
            {STAGES.map((s, i) => (
              <div key={s.key} className="flex flex-col items-center flex-1">
                <div className={`relative ${i === sIdx ? '' : 'opacity-40 grayscale'}`}>
                  <TurulMascot mood={i === sIdx ? 'happy' : 'idle'} color={config.color} size={i === sIdx ? 56 : 42} animate={false} shadow={false} />
                </div>
                <span className={`text-[10px] font-semibold mt-1 ${i === sIdx ? 'text-turul-blue' : 'text-slate-400'}`}>
                  {s.name[lang] ?? s.name.hu}
                </span>
                <span className="text-[9px] text-slate-400">{s.minGrade}–{s.maxGrade}.</span>
              </div>
            ))}
          </div>
        </section>

        {/* Color customization */}
        <section className="card p-4">
          <h2 className="font-bold text-slate-800 mb-3">{t('companion.color')}</h2>
          <div className="flex gap-3">
            {COLOR_OPTIONS.map(col => (
              <button
                key={col}
                onClick={() => update({ color: col })}
                className={`w-12 h-12 rounded-full transition-all ${
                  config.color === col ? 'ring-4 ring-offset-2 ring-slate-300 scale-105' : 'hover:scale-105'
                }`}
                style={{ backgroundColor: COLOR_SWATCH[col] }}
                aria-label={col}
              />
            ))}
          </div>
        </section>

        {/* Accessory customization */}
        <section className="card p-4">
          <h2 className="font-bold text-slate-800 mb-3">{t('companion.accessory')}</h2>
          <div className="grid grid-cols-4 gap-2">
            {ACCESSORY_OPTIONS.map(acc => (
              <button
                key={acc}
                onClick={() => update({ accessory: acc })}
                className={`flex flex-col items-center gap-1 py-3 rounded-xl border-2 transition-all ${
                  config.accessory === acc
                    ? 'border-turul-blue bg-brand-50'
                    : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <TurulMascot mood="idle" color={config.color} accessory={acc} size={40} animate={false} shadow={false} />
                <span className={`text-[10px] font-semibold ${config.accessory === acc ? 'text-turul-blue' : 'text-slate-500'}`}>
                  {ACCESSORY_LABEL[acc][lang] ?? ACCESSORY_LABEL[acc].hu}
                </span>
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3">{t('companion.more.soon')}</p>
        </section>
      </div>

      <BottomNav />
    </div>
  )
}
