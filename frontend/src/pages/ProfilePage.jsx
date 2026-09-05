import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import BottomNav from '../components/BottomNav'
import TurulPortrait from '../components/TurulPortrait'
import InstallAppBanner from '../components/InstallAppBanner'
import { stageForGrade } from '../lib/turul'

const GRADES = Array.from({ length: 8 }, (_, i) => i + 5) // 5..12
const MODES = ['text', 'story', 'visual', 'quiz']
const MODE_EMOJI = { text: '📖', story: '🎭', visual: '🗺️', quiz: '🧠' }

export default function ProfilePage() {
  const { session, setProfile, signOut } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [confirmingSignOut, setConfirmingSignOut] = useState(false)

  const token = session?.access_token

  useEffect(() => {
    api.account.me(token)
      .then(p => setForm({
        display_name: p.display_name ?? '',
        grade: p.grade ?? 7,
        preferred_mode: p.preferred_mode ?? 'text',
      }))
      .catch(() => navigate('/onboarding'))
  }, [token, navigate])

  function set(key, val) {
    setForm(f => ({ ...f, [key]: val }))
    setSaved(false)
  }

  async function save() {
    setSaving(true)
    setError('')
    try {
      const updated = await api.account.update(form, token)
      setProfile(Array.isArray(updated) ? updated[0] : updated)
      setSaved(true)
    } catch (err) {
      setError(err.message ?? 'Hiba a mentéskor')
    } finally {
      setSaving(false)
    }
  }

  if (!form) {
    return <div className="flex h-screen items-center justify-center text-slate-400">{t('common.loading')}</div>
  }

  const stage = stageForGrade(form.grade)

  return (
    <div className="pb-28">
      <PageHeader title={t('profile.title')} backTo="/" />

      <div className="px-4 py-5 max-w-lg mx-auto space-y-5">
        {/* Live Turul preview — updates as you change grade */}
        <div className="card p-5 flex items-center gap-4">
          <TurulPortrait grade={form.grade} size={80} animate={false} />
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide text-turul-blue">{stage.name[lang] ?? stage.name.hu}</p>
            <p className="text-sm text-slate-500 mt-0.5">{t('profile.stage.hint')}</p>
          </div>
        </div>

        {/* Name */}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-1.5">{t('profile.name')}</label>
          <input
            type="text"
            value={form.display_name}
            onChange={e => set('display_name', e.target.value)}
            className="input"
            placeholder={t('onboard.name.ph')}
          />
        </div>

        {/* Grade */}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">{t('profile.grade')}</label>
          <div className="grid grid-cols-4 gap-2.5">
            {GRADES.map(g => (
              <button
                key={g}
                onClick={() => set('grade', g)}
                className={`py-3.5 rounded-xl font-bold text-lg transition-all ${
                  form.grade === g
                    ? 'bg-turul-blue text-white shadow-glow-blue scale-105'
                    : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                {g}.
              </button>
            ))}
          </div>
        </div>

        {/* Preferred mode */}
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">{t('profile.mode')}</label>
          <div className="grid grid-cols-2 gap-2.5">
            {MODES.map(m => (
              <button
                key={m}
                onClick={() => set('preferred_mode', m)}
                className={`flex items-center gap-2 px-3 py-3 rounded-xl border-2 font-semibold text-sm transition-all ${
                  form.preferred_mode === m
                    ? 'border-turul-blue bg-brand-50 text-turul-blue'
                    : 'border-slate-200 text-slate-700 hover:border-slate-300'
                }`}
              >
                <span>{MODE_EMOJI[m]}</span> {t(`mode.${m}`)}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button onClick={save} disabled={saving || !form.display_name.trim()} className="btn-primary w-full">
          {saving ? t('auth.loading') : saved ? `✓ ${t('profile.saved')}` : t('profile.save')}
        </button>

        {/* Always visible here (unlike Home's dismissible card) — a stable place to
            find the install option even after dismissing it once on Home. */}
        <div className="pt-4 border-t border-slate-100">
          <InstallAppBanner variant="inline" />
        </div>

        {/* Sign out — visually separated + requires confirmation, so it can't be
            mistaken for a "close settings" action (users have tapped it by accident). */}
        <div className="pt-3 mt-1 border-t border-slate-100">
          {confirmingSignOut ? (
            <div className="flex flex-col gap-2.5 pt-3">
              <p className="text-sm text-slate-500 text-center">{t('profile.signout.confirm')}</p>
              <div className="flex gap-2">
                <button
                  onClick={() => setConfirmingSignOut(false)}
                  className="flex-1 px-3 py-2.5 rounded-xl text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200"
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={signOut}
                  className="flex-1 px-3 py-2.5 rounded-xl text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100"
                >
                  {t('profile.signout.confirm.cta')}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setConfirmingSignOut(true)}
              className="w-full text-center text-sm font-semibold text-red-500 py-2.5 hover:text-red-600"
            >
              🚪 {t('home.signout')}
            </button>
          )}
        </div>
      </div>

      <BottomNav />
    </div>
  )
}
