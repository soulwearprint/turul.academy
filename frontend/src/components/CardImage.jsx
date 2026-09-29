import { useEffect, useState } from 'react'
import { useLang } from '../contexts/LanguageContext'
import { mediaUrl } from '../lib/media'

// A card's picture (content card field `image`):
//   { src, alt, w, h, credit, source }  — src: storage path or URL; credit: author · license;
//   source: the page the licence points to (e.g. the Wikimedia Commons file page).
// Tapping opens a full-screen viewer — maps are unreadable at phone width otherwise.
export default function CardImage({ image, dark = false }) {
  const { t } = useLang()
  const [open, setOpen] = useState(false)
  const url = mediaUrl(image?.src)
  if (!url) return null
  const ratio = image.w && image.h ? { aspectRatio: `${image.w} / ${image.h}` } : undefined

  return (
    <figure className="flex flex-col gap-1.5">
      <button type="button" onClick={() => setOpen(true)} aria-label={t('media.zoom')}
        className={`relative block w-full overflow-hidden rounded-xl ${dark ? 'bg-white/5' : 'bg-slate-100'}`}>
        <img src={url} alt={image.alt || ''} loading="lazy" decoding="async" style={ratio}
          className="w-full h-auto max-h-[65vh] object-contain" />
        {/* Icon only: a text badge covered axis labels on the small diagrams. */}
        <span aria-hidden="true" className="absolute bottom-1.5 right-1.5 w-7 h-7 grid place-items-center rounded-full bg-black/45 text-[13px]">
          🔍
        </span>
      </button>
      {(image.credit || image.source) && (
        <figcaption className={`text-[10px] leading-snug ${dark ? 'text-white/45' : 'text-slate-400'}`}>
          {image.credit}
          {image.source && (
            <>{image.credit ? ' · ' : ''}<a href={image.source} target="_blank" rel="noopener noreferrer" className="underline">{t('media.source')}</a></>
          )}
        </figcaption>
      )}
      {open && <ImageViewer url={url} alt={image.alt} onClose={() => setOpen(false)} />}
    </figure>
  )
}

// Full-screen viewer: fits the screen; tap the picture to zoom to 2.5× and pan by scrolling.
// (Native pinch-zoom still works too — the viewport meta doesn't disable it.)
function ImageViewer({ url, alt, onClose }) {
  const { t } = useLang()
  const [zoomed, setZoomed] = useState(false)

  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose() }
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = prev }
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 bg-black flex flex-col" role="dialog" aria-modal="true" aria-label={alt || ''}>
      <div className="flex items-center justify-between px-4 py-3 text-white">
        <button type="button" onClick={() => setZoomed(z => !z)} className="text-sm font-semibold bg-white/15 rounded-full px-3 py-1.5">
          {zoomed ? '－' : '＋'} {t(zoomed ? 'media.fit' : 'media.zoom')}
        </button>
        <button type="button" onClick={onClose} aria-label={t('media.close')}
          className="text-2xl leading-none w-10 h-10 rounded-full bg-white/15">×</button>
      </div>
      <div className="flex-1 overflow-auto" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
        <img src={url} alt={alt || ''} onClick={() => setZoomed(z => !z)}
          className={zoomed ? 'max-w-none w-[250%] h-auto cursor-zoom-out' : 'w-full h-full object-contain cursor-zoom-in'} />
      </div>
    </div>
  )
}

// Visual card field `timeline`: [{ when, what }] — rendered natively (a picture of text
// would be unreadable on a phone and couldn't be fixed from the review queue).
export function Timeline({ items }) {
  return (
    <ol className="relative ml-2 border-l-2 border-turul-blue/25 flex flex-col gap-3.5 py-1">
      {items.map((it, i) => (
        <li key={i} className="relative pl-5">
          <span className="absolute -left-[8px] top-1 w-3.5 h-3.5 rounded-full bg-turul-blue ring-4 ring-white" />
          <p className="text-xs font-bold text-turul-blue tracking-wide">{it.when}</p>
          <p className="text-sm text-slate-700 leading-snug mt-0.5">{it.what}</p>
        </li>
      ))}
    </ol>
  )
}
