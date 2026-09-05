import React from 'react'
import ReactDOM from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

// registerType: 'prompt' (see vite.config.js) — a new deploy doesn't silently swap the
// app shell under a student mid-lesson; they confirm the reload themselves.
const updateSW = registerSW({
  onNeedRefresh() {
    if (window.confirm('Elérhető egy új verzió a Turulból. Frissítsük most?')) {
      updateSW(true)
    }
  },
  onOfflineReady() {
    console.info('Turul: offline-ra kész — a megnyitott leckék internet nélkül is elérhetők.')
  },
})
