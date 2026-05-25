import { useNavigate } from 'react-router-dom'

export default function PageHeader({ title, subtitle, backTo }) {
  const navigate = useNavigate()

  return (
    <header className="sticky top-0 bg-white border-b border-slate-100 z-40 px-4 py-3">
      <div className="flex items-center gap-3 max-w-lg mx-auto">
        {backTo && (
          <button
            onClick={() => navigate(backTo)}
            className="w-9 h-9 flex items-center justify-center rounded-xl hover:bg-slate-100 text-slate-500 shrink-0"
          >
            ←
          </button>
        )}
        <div className="min-w-0">
          <h1 className="font-bold text-slate-900 truncate">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 truncate">{subtitle}</p>}
        </div>
      </div>
    </header>
  )
}
