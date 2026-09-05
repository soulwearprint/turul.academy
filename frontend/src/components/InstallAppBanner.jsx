import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { useInstallPrompt, isIOS } from '../lib/useInstallPrompt'

const DISMISS_KEY = 'turul_install_banner_dismissed'

// Cross-platform "install as app" prompt.
// - Android/Chrome/desktop: real one-tap install via the captured beforeinstallprompt event.
// - iOS Safari: no programmatic install API exists — Apple doesn't expose one — so instead
//   of a fake button, we show the actual manual steps (Share → Add to Home Screen).
// - A QR code (same URL either way — it's one PWA, not separate apps) is included so
//   someone viewing this on a desktop can get their phone to the same page in one scan;
//   what happens after that still depends on the phone's own browser.
export default function InstallAppBanner({ variant = 'card' }) {
  const { canInstall, installed, promptInstall } = useInstallPrompt()
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(DISMISS_KEY) === '1')
  const [showQR, setShowQR] = useState(variant === 'inline')
  const [qrDataUrl, setQrDataUrl] = useState(null)
  const ios = isIOS()

  useEffect(() => {
    if (!showQR || qrDataUrl) return
    QRCode.toDataURL(window.location.origin, { width: 200, margin: 1, color: { dark: '#0F172A', light: '#00000000' } })
      .then(setQrDataUrl)
      .catch(() => {})
  }, [showQR, qrDataUrl])

  if (installed) return null
  if (variant === 'card' && dismissed) return null

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, '1')
    setDismissed(true)
  }

  async function handleInstall() {
    const outcome = await promptInstall()
    if (outcome === 'accepted') setDismissed(true)
  }

  const wrapCls = variant === 'card'
    ? 'card p-4 flex flex-col gap-3 animate-fade-up'
    : 'flex flex-col gap-3'

  return (
    <div className={wrapCls}>
      <div className="flex items-start gap-3">
        <span className="text-2xl">📲</span>
        <div className="min-w-0 flex-1">
          <p className="font-bold text-slate-900 text-sm">Telepítsd a Turult alkalmazásként</p>
          <p className="text-xs text-slate-500 mt-0.5">
            Gyorsabb indítás, teljes képernyő, és a megnyitott leckék internet nélkül is elérhetők.
          </p>
        </div>
        {variant === 'card' && (
          <button onClick={dismiss} className="text-slate-300 hover:text-slate-500 text-lg leading-none" aria-label="Bezárás">×</button>
        )}
      </div>

      {canInstall && (
        <button onClick={handleInstall} className="btn-primary h-11 rounded-xl text-sm">
          Telepítés
        </button>
      )}

      {!canInstall && ios && (
        <p className="text-xs text-slate-600 bg-slate-50 rounded-xl px-3 py-2.5 leading-relaxed">
          iPhone-on nincs egygombos telepítés — koppints a Megosztás <span className="font-semibold">⬆️</span> gombra,
          majd válaszd: <span className="font-semibold">„Kezdőképernyőhöz adás”</span>.
        </p>
      )}

      {!canInstall && !ios && (
        <p className="text-xs text-slate-500">
          Ezen a böngészőn most nem kínálható egygombos telepítés — nyisd meg telefonon az alábbi QR-kóddal, ott is elérhető lesz a telepítés.
        </p>
      )}

      {variant === 'card' && (
        <button onClick={() => setShowQR(s => !s)} className="text-xs font-semibold text-turul-blue text-left">
          {showQR ? 'QR-kód elrejtése' : '📱 Áttelepítés másik eszközre — QR-kód'}
        </button>
      )}

      {showQR && (
        <div className="flex items-center gap-3 bg-slate-50 rounded-xl p-3">
          {qrDataUrl
            ? <img src={qrDataUrl} alt="QR kód a Turul megnyitásához" width={92} height={92} className="rounded-lg" />
            : <div className="w-[92px] h-[92px] rounded-lg bg-slate-200 animate-pulse" />}
          <p className="text-xs text-slate-500 leading-relaxed">
            Olvasd be a telefonod kamerájával, nyisd meg a linket, majd kövesd a telepítési lépéseket
            (Androidon a fenti gomb, iPhone-on a Megosztás menü).
          </p>
        </div>
      )}
    </div>
  )
}
