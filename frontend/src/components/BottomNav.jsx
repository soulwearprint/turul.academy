import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',          label: 'Ma',        icon: '🏠' },
  { to: '/subjects',  label: 'Tantárgyak', icon: '📚' },
  { to: '/progress',  label: 'Haladás',   icon: '📊' },
]

export default function BottomNav() {
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
    </nav>
  )
}
