import { NavLink } from 'react-router-dom'
import { useLang } from '../contexts/LanguageContext'
import { getTurulConfig } from '../lib/turul'
import TurulMascot from './TurulMascot'

function Icon({ name, active }) {
  const stroke = active ? '#2563EB' : '#94A3B8'
  const common = { width: 24, height: 24, viewBox: '0 0 24 24', fill: 'none', stroke, strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' }
  if (name === 'home') return <svg {...common}><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5" /></svg>
  if (name === 'subjects') return <svg {...common}><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" /><path d="M19 17H6a2 2 0 0 0-2 2" /></svg>
  if (name === 'progress') return <svg {...common}><path d="M3 3v18h18" /><path d="M7 14l3-4 3 2 4-6" /></svg>
  return null
}

export default function BottomNav() {
  const { t, lang, setLang } = useLang()
  const config = getTurulConfig()

  const links = [
    { to: '/',         label: t('nav.home'),     icon: 'home' },
    { to: '/subjects', label: t('nav.subjects'), icon: 'subjects' },
    { to: '/progress', label: t('nav.progress'), icon: 'progress' },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur border-t border-slate-100 flex items-stretch safe-bottom z-50">
      {links.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `relative flex-1 flex flex-col items-center pt-2.5 pb-2 gap-0.5 text-[11px] font-semibold transition-colors ${
              isActive ? 'text-turul-blue' : 'text-slate-400'
            }`
          }
        >
          {({ isActive }) => (
            <>
              {isActive && <span className="absolute top-0 h-0.5 w-8 rounded-full bg-turul-blue" />}
              <Icon name={icon} active={isActive} />
              {label}
            </>
          )}
        </NavLink>
      ))}

      {/* Turul companion tab */}
      <NavLink
        to="/turul"
        className={({ isActive }) =>
          `relative flex-1 flex flex-col items-center pt-1.5 pb-2 gap-0.5 text-[11px] font-semibold transition-colors ${
            isActive ? 'text-turul-blue' : 'text-slate-400'
          }`
        }
      >
        {({ isActive }) => (
          <>
            {isActive && <span className="absolute top-0 h-0.5 w-8 rounded-full bg-turul-blue" />}
            <TurulMascot mood={isActive ? 'happy' : 'idle'} color={config.color} size={28} animate={false} shadow={false} />
            {t('nav.turul')}
          </>
        )}
      </NavLink>

      {/* Language toggle */}
      <button
        onClick={() => setLang(lang === 'hu' ? 'en' : 'hu')}
        className="flex flex-col items-center justify-center px-3 gap-0.5 text-[11px] font-bold text-slate-400 hover:text-slate-600 transition-colors"
        title={lang === 'hu' ? 'Switch to English' : 'Váltás magyarra'}
      >
        <span className="text-lg leading-none">{lang === 'hu' ? '🇭🇺' : '🇬🇧'}</span>
        {lang === 'hu' ? 'EN' : 'HU'}
      </button>
    </nav>
  )
}
