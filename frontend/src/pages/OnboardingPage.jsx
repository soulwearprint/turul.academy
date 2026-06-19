import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import TurulPortrait from '../components/TurulPortrait'
import { stageForGrade } from '../lib/turul'

const GRADES = Array.from({ length: 8 }, (_, i) => i + 5) // 5..12
const MODES  = ['text', 'story', 'visual', 'quiz']
const MODE_EMOJI = { text: '📖', story: '🎭', visual: '🗺️', quiz: '🧠' }

export default function OnboardingPage() {
  const { session, setProfile } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    display_name: '',
    grade: 7,
    birth_year: new Date().getFullYear() - 13,
    preferred_mode: 'text',
    language: lang,
    gamification_level: 'light',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function set(key, val) { setForm(f => ({ ...f, [key]: val })) }

  async function finish() {
    setLoading(true)
    setError('')
    try {
      const profile = await api.account.create(form, session?.access_token)
      setProfile(profile)
      navigate('/subjects')
    } catch (err) {
      setError(err.message ?? 'Hiba a profil létrehozásakor')
    } finally {
      setLoading(false)
    }
  }

  const stage = stageForGrade(form.grade)

  const steps = [
    // Step 0 — name
    <div key="name" className="space-y-5">
      <h2 className="text-2xl font-extrabold text-slate-900 font-display">{t('onboard.name.q')}</h2>
      <input
        autoFocus
        type="text"
        value={form.display_name}
        onChange={e => set('display_name', e.target.value)}
        placeholder={t('onboard.name.ph')}
        className="input text-lg"
      />
    </div>,

    // Step 1 — grade
    <div key="grade" className="space-y-5">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-900 font-display">{t('onboard.grade.q')}</h2>
        <p className="text-sm text-turul-blue font-semibold mt-1">{stage.name[lang] ?? stage.name.hu}</p>
      </div>
      <div className="grid grid-cols-4 gap-2.5">
        {GRADES.map(g => (
          <button
            key={g}
            onClick={() => set('grade', g)}
            className={`py-4 rounded-xl font-bold text-lg transition-all ${
              form.grade === g
                ? 'bg-turul-blue text-white shadow-glow-blue scale-105'
                : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
            }`}
          >
            {g}.
          </button>
        ))}
      </div>
    </div>,

    // Step 2 — preferred mode
    <div key="mode" className="space-y-4">
      <div>
        <h2 className="text-2xl font-extrabold text-slate-900 font-display">{t('onboard.mode.q')}</h2>
        <p className="text-slate-500 text-sm mt-1">{t('onboard.mode.hint')}</p>
      </div>
      <div className="space-y-2.5">
        {MODES.map(m => (
          <button
            key={m}
            onClick={() => set('preferred_mode', m)}
            className={`w-full flex items-center gap-3 text-left px-4 py-3.5 rounded-xl border-2 font-semibold transition-all ${
              form.preferred_mode === m
                ? 'border-turul-blue bg-brand-50 text-turul-blue'
                : 'border-slate-200 text-slate-700 hover:border-slate-300'
            }`}
          >
            <span className="text-xl">{MODE_EMOJI[m]}</span>
            <span>{t(`mode.${m}`)}</span>
            <span className="ml-auto text-xs font-normal text-slate-400">{t(`mode.${m}.desc`)}</span>
          </button>
        ))}
      </div>
    </div>,
  ]

  const canNext = step === 0 ? form.display_name.trim().length > 0 : true

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Progress bar */}
      <div className="h-1.5 bg-slate-200">
        <div
          className="h-full bg-turul-blue transition-all duration-500"
          style={{ width: `${((step + 1) / steps.length) * 100}%` }}
        />
      </div>

      <div className="flex-1 flex flex-col px-5 py-6 max-w-sm mx-auto w-full">
        {/* Mascot guide */}
        <div className="flex flex-col items-center text-center mb-2">
          <TurulPortrait grade={form.grade} size={120} />
          <div className="text-xs text-slate-400 font-medium mt-1">{step + 1} / {steps.length}</div>
        </div>

        <div className="flex-1">{steps[step]}</div>

        {error && <p className="text-red-500 text-sm mb-3">{error}</p>}

        <div className="space-y-2.5 mt-6">
          {step < steps.length - 1 ? (
            <button
              disabled={!canNext}
              onClick={() => setStep(s => s + 1)}
              className="btn-primary w-full"
            >
              {t('onboard.next')}
            </button>
          ) : (
            <button
              disabled={loading}
              onClick={finish}
              className="btn-primary w-full"
            >
              {loading ? t('auth.loading') : t('onboard.start')}
            </button>
          )}
          {step > 0 && (
            <button onClick={() => setStep(s => s - 1)} className="btn-secondary w-full">
              {t('onboard.back')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
