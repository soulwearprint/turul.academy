import { NavLink } from 'react-router-dom'
import { useLang } from '../contexts/LanguageContext'

export default function BottomNav() {
  const { t, lang, setLang } = useLang()

  const links = [
    { to: '/',         label: t('nav.home'),     icon: '🏠' },
    { to: '/subjects', label: t('nav.subjects'),  icon: '📚' },
    { to: '/progress', label: t('nav.progress'),  icon: '📊' },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-100 flex safe-bottom z-50">
      {links.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center py-3 gap-0.5 text-xs font-medium transition-colors ${
              isActive ? 'text-turul-blue' : 'text-slate-400'
            }`
          }
        >
          <span className="text-xl leading-none">{icon}</span>
          {label}
        </NavLink>
      ))}

      {/* Language toggle */}
      <button
        onClick={() => setLang(lang === 'hu' ? 'en' : 'hu')}
        className="flex flex-col items-center py-3 px-3 gap-0.5 text-xs font-semibold text-slate-400 hover:text-slate-600 transition-colors"
        title={lang === 'hu' ? 'Switch to English' : 'Váltás magyarra'}
      >
        <span className="text-xl leading-none">{lang === 'hu' ? '🇭🇺' : '🇬🇧'}</span>
        {lang === 'hu' ? 'EN' : 'HU'}
      </button>
    </nav>
  )
}
