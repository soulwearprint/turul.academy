import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'

const GRADES = Array.from({ length: 8 }, (_, i) => i + 5) // 5..12
const MODES  = ['text', 'story', 'visual', 'quiz']
const MODE_LABELS = { text: '📖 Szöveg', story: '🎭 Történet', visual: '🗺️ Vizuális', quiz: '🧠 Kvíz' }

export default function OnboardingPage() {
  const { session, setProfile } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    display_name: '',
    grade: 7,
    birth_year: new Date().getFullYear() - 13,
    preferred_mode: 'text',
    language: 'hu',
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

  const steps = [
    // Step 0 — name
    <div key="name" className="space-y-4">
      <h2 className="text-xl font-bold">Hogy szólítsunk?</h2>
      <input
        autoFocus
        type="text"
        value={form.display_name}
        onChange={e => set('display_name', e.target.value)}
        placeholder="Beceneved"
        className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-turul-blue"
      />
    </div>,

    // Step 1 — grade
    <div key="grade" className="space-y-4">
      <h2 className="text-xl font-bold">Melyik osztályba jársz?</h2>
      <div className="grid grid-cols-4 gap-2">
        {GRADES.map(g => (
          <button
            key={g}
            onClick={() => set('grade', g)}
            className={`py-3 rounded-xl font-bold text-lg transition-all ${
              form.grade === g
                ? 'bg-turul-blue text-white shadow-md scale-105'
                : 'bg-slate-100 text-slate-600'
            }`}
          >
            {g}.
          </button>
        ))}
      </div>
    </div>,

    // Step 2 — preferred mode
    <div key="mode" className="space-y-4">
      <h2 className="text-xl font-bold">Hogyan tanulsz szívesebben?</h2>
      <p className="text-slate-500 text-sm">Ezt bármikor megváltoztathatod.</p>
      <div className="space-y-2">
        {MODES.map(m => (
          <button
            key={m}
            onClick={() => set('preferred_mode', m)}
            className={`w-full text-left px-4 py-3 rounded-xl border-2 font-medium transition-all ${
              form.preferred_mode === m
                ? 'border-turul-blue bg-blue-50 text-turul-blue'
                : 'border-slate-200 text-slate-700'
            }`}
          >
            {MODE_LABELS[m]}
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

      <div className="flex-1 flex flex-col px-5 py-8 max-w-sm mx-auto w-full">
        <div className="mb-2 text-xs text-slate-400 font-medium">
          {step + 1} / {steps.length}
        </div>

        <div className="flex-1">{steps[step]}</div>

        {error && <p className="text-red-500 text-sm mb-3">{error}</p>}

        <div className="space-y-2 mt-6">
          {step < steps.length - 1 ? (
            <button
              disabled={!canNext}
              onClick={() => setStep(s => s + 1)}
              className="btn-primary w-full text-center"
            >
              Tovább →
            </button>
          ) : (
            <button
              disabled={loading}
              onClick={finish}
              className="btn-primary w-full text-center"
            >
              {loading ? '...' : 'Kezdjük el! 🚀'}
            </button>
          )}
          {step > 0 && (
            <button onClick={() => setStep(s => s - 1)} className="btn-secondary w-full text-center">
              ← Vissza
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
