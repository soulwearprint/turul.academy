import { createContext, useContext, useState, useEffect } from 'react'
import { translate } from '../lib/i18n'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    return localStorage.getItem('ta_lang') || 'hu'
  })

  function setLang(l) {
    localStorage.setItem('ta_lang', l)
    setLangState(l)
  }

  function t(key, vars = {}) {
    return translate(key, lang, vars)
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLang() {
  const ctx = useContext(LanguageContext)
  if (!ctx) throw new Error('useLang must be used inside LanguageProvider')
  return ctx
}
