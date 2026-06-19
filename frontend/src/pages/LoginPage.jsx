import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import TurulMascot from '../components/TurulMascot'

export default function LoginPage() {
  const { signInWithEmail, signUpWithEmail } = useAuth()
  const { t, lang, setLang } = useLang()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await signInWithEmail(email, password)
        navigate('/')
      } else {
        await signUpWithEmail(email, password)
        navigate('/onboarding')
      }
    } catch (err) {
      setError(err.message ?? 'Ismeretlen hiba')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Hero */}
      <div className="hero-gradient relative px-5 pt-14 pb-20 text-center overflow-hidden">
        <button
          onClick={() => setLang(lang === 'hu' ? 'en' : 'hu')}
          className="absolute top-5 right-5 chip hover:bg-white/25 transition-colors"
        >
          {lang === 'hu' ? '🇬🇧 EN' : '🇭🇺 HU'}
        </button>

        <div className="mx-auto mt-2 inline-flex items-center justify-center rounded-full bg-white shadow-lift ring-1 ring-black/5" style={{ width: 148, height: 148 }}>
          <TurulMascot mood="happy" size={118} shadow={false} />
        </div>
        <h1 className="mt-4 text-4xl font-extrabold text-white tracking-tight font-display">Turul</h1>
        <p className="mt-2 text-brand-100 text-[15px] max-w-xs mx-auto leading-relaxed">{t('auth.tagline')}</p>
      </div>

      {/* Auth card overlapping the hero */}
      <div className="px-5 -mt-12 pb-10 flex-1">
        <div className="card p-6 max-w-sm mx-auto animate-fade-up">
          <div className="flex rounded-xl bg-slate-100 p-1 mb-5">
            {['login', 'signup'].map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setError('') }}
                className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  mode === m ? 'bg-white shadow-soft text-turul-blue' : 'text-slate-500'
                }`}
              >
                {m === 'login' ? t('auth.login') : t('auth.register')}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">{t('auth.email')}</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="input"
                placeholder="te@iskola.hu"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">{t('auth.password')}</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="input"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3 border border-red-100">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? t('auth.loading') : mode === 'login' ? t('auth.submit.login') : t('auth.submit.reg')}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6 max-w-xs mx-auto leading-relaxed">
          {t('auth.legal')}
        </p>
      </div>
    </div>
  )
}
