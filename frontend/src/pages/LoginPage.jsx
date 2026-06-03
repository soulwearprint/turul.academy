import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'

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
    <div className="min-h-screen flex flex-col items-center justify-center px-5 bg-gradient-to-b from-turul-blue to-brand-700">
      {/* Language toggle */}
      <div className="absolute top-4 right-4">
        <button
          onClick={() => setLang(lang === 'hu' ? 'en' : 'hu')}
          className="text-white/70 hover:text-white text-sm font-semibold flex items-center gap-1.5"
        >
          {lang === 'hu' ? '🇬🇧 EN' : '🇭🇺 HU'}
        </button>
      </div>

      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-3">🦅</div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Turul Academy</h1>
          <p className="text-brand-200 mt-1 text-sm">{t('auth.tagline')}</p>
        </div>

        {/* Card */}
        <div className="card p-6">
          <div className="flex rounded-xl bg-slate-100 p-1 mb-5">
            {['login', 'signup'].map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setError('') }}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all ${
                  mode === m ? 'bg-white shadow text-slate-900' : 'text-slate-500'
                }`}
              >
                {m === 'login' ? t('auth.login') : t('auth.register')}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('auth.email')}</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-turul-blue"
                placeholder="te@iskola.hu"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">{t('auth.password')}</label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-turul-blue"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-3">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full text-center">
              {loading ? t('auth.loading') : mode === 'login' ? t('auth.submit.login') : t('auth.submit.reg')}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
