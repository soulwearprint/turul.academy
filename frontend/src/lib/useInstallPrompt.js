import { useEffect, useState } from 'react'

// Captures the browser's `beforeinstallprompt` event (Chromium/Android/desktop only —
// iOS Safari never fires this, there is no programmatic install API there) and reports
// whether the app is already running installed (standalone display mode).
export function useInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [installed, setInstalled] = useState(
    () => window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
  )

  useEffect(() => {
    function onBeforeInstall(e) {
      e.preventDefault()
      setDeferredPrompt(e)
    }
    function onInstalled() {
      setInstalled(true)
      setDeferredPrompt(null)
    }
    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [])

  async function promptInstall() {
    if (!deferredPrompt) return null
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    setDeferredPrompt(null)
    return outcome // 'accepted' | 'dismissed'
  }

  return { canInstall: !!deferredPrompt, installed, promptInstall }
}

export function isIOS() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent)
}
