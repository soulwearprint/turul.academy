import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// Progress/quiz-submit POSTs get NetworkOnly + backgroundSync: if the request fails
// (offline), Workbox queues it in IndexedDB and the browser replays it automatically
// once connectivity returns — no custom sync code needed on our side. GET content
// endpoints use StaleWhileRevalidate so an already-opened lesson/topic/quiz stays
// readable offline, while still refreshing in the background whenever online.
const OFFLINE_SYNC_ROUTES = [
  { pattern: /\/api\/nat\/lessons\/[^/]+\/progress$/, name: 'nat-progress-queue' },
  { pattern: /\/api\/lessons\/[^/]+\/progress$/,       name: 'legacy-progress-queue' },
  { pattern: /\/api\/nat\/quiz\/submit$/,               name: 'nat-quiz-queue' },
  { pattern: /\/api\/quiz\/submit$/,                    name: 'legacy-quiz-queue' },
]

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'prompt', // we show our own "new version available" prompt (see main.jsx)
      includeAssets: ['favicon.ico', 'favicon-32.png', 'apple-touch-icon.png'],
      manifest: {
        name: 'Turul — AI tanulótárs',
        short_name: 'Turul',
        description: 'Turul: AI tanulótárs magyar diákoknak. NAT-alapú tananyag, személyre szabva.',
        lang: 'hu',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        background_color: '#F8FAFC',
        theme_color: '#2563EB',
        icons: [
          // Not marked "maskable" — the mascot art runs edge-to-edge, so Android's
          // adaptive-icon crop would clip the wingtips/feet. A dedicated padded
          // export would be needed before adding a maskable variant.
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
        ],
      },
      workbox: {
        // Precache the built app shell (JS/CSS/HTML) — Workbox fills this in at build time.
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          // Already-opened lesson/topic/quiz content: available offline, refreshed
          // in the background whenever online. Never cache /api/account or /api/*progress*
          // (me) reads — those must reflect live, user-specific state, not a stale copy.
          {
            urlPattern: /\/api\/(nat\/(lessons|topics)(\/[^/]+)?(\/quiz)?|curriculum\/(subjects|topics))(\?.*)?$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'nat-content',
              cacheableResponse: { statuses: [0, 200] },
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
          ...OFFLINE_SYNC_ROUTES.map(({ pattern, name }) => ({
            urlPattern: pattern,
            method: 'POST',
            handler: 'NetworkOnly',
            options: {
              backgroundSync: {
                name,
                options: { maxRetentionTime: 24 * 60 }, // retry for up to 24h
              },
            },
          })),
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8003',  // Academy's dedicated port — see port map in memory docs
        changeOrigin: true,
      },
    },
  },
})
