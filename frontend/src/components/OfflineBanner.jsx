import { useEffect, useState } from 'react'

export default function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine)

  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])

  if (online) return null
  return (
    <div className="fixed top-0 inset-x-0 z-50 bg-slate-900 text-white text-xs font-semibold text-center py-1.5">
      📡 Nincs internetkapcsolat — a megnyitott leckék elérhetők, az aktivitás a kapcsolat helyreállása után szinkronizálódik.
    </div>
  )
}
