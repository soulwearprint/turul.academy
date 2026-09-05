import { useId } from 'react'

// Renders a structured shape list (from the physics `experiment` mode's `sketch`
// field) as a hand-drawn-looking SVG, via a shared feTurbulence/feDisplacementMap
// filter — same wobble applied to every diagram so they read as one consistent
// "teacher sketched this on the board" style rather than sterile technical drawings.

const DEFAULT_VIEWBOX = '0 0 400 300'

function zigzagPoints(x1, y1, x2, y2, coils = 6, amp = 10) {
  const segs = coils * 2
  const dx = (x2 - x1) / segs
  const dy = (y2 - y1) / segs
  const len = Math.hypot(x2 - x1, y2 - y1) || 1
  const nx = -(y2 - y1) / len
  const ny = (x2 - x1) / len
  const pts = [`${x1},${y1}`]
  for (let i = 1; i < segs; i++) {
    const px = x1 + dx * i
    const py = y1 + dy * i
    const off = i % 2 === 0 ? 0 : amp
    pts.push(`${px + nx * off},${py + ny * off}`)
  }
  pts.push(`${x2},${y2}`)
  return pts.join(' ')
}

function Shape({ shape: s }) {
  switch (s.type) {
    case 'box':
      return <rect x={s.x} y={s.y} width={s.w} height={s.h} rx="2" fill="none" stroke="currentColor" strokeWidth="2" />

    case 'circle':
      return <circle cx={s.x} cy={s.y} r={s.r} fill="none" stroke="currentColor" strokeWidth="2" />

    case 'line':
      return (
        <line x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} stroke="currentColor" strokeWidth="2"
          strokeDasharray={s.dashed ? '6 5' : undefined} />
      )

    case 'arrow': {
      const angle = Math.atan2(s.y2 - s.y1, s.x2 - s.x1)
      const ah = 8
      const p1x = s.x2 - ah * Math.cos(angle - Math.PI / 7)
      const p1y = s.y2 - ah * Math.sin(angle - Math.PI / 7)
      const p2x = s.x2 - ah * Math.cos(angle + Math.PI / 7)
      const p2y = s.y2 - ah * Math.sin(angle + Math.PI / 7)
      return (
        <g stroke="currentColor" strokeWidth="2" fill="none">
          <line x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} />
          <polyline points={`${p1x},${p1y} ${s.x2},${s.y2} ${p2x},${p2y}`} />
        </g>
      )
    }

    case 'coil': {
      const turns = s.turns || 5
      const step = s.w / turns
      return (
        <g fill="none" stroke="currentColor" strokeWidth="2">
          {Array.from({ length: turns }, (_, i) => (
            <ellipse key={i} cx={s.x + step * i + step / 2} cy={s.y + s.h / 2} rx={step / 2} ry={s.h / 2} />
          ))}
        </g>
      )
    }

    case 'spring':
      return (
        <polyline points={zigzagPoints(s.x1, s.y1, s.x2, s.y2, s.coils || 6)}
          fill="none" stroke="currentColor" strokeWidth="2" />
      )

    case 'dot':
      return <circle cx={s.x} cy={s.y} r="3" fill="currentColor" />

    case 'triangle': {
      const sz = s.size || 14
      const points = `${s.x},${s.y - sz} ${s.x - sz},${s.y + sz} ${s.x + sz},${s.y + sz}`
      return <polygon points={points} fill="none" stroke="currentColor" strokeWidth="2" />
    }

    case 'wave': {
      const cycles = s.cycles || 4
      const amp = s.amplitude || 10
      const dx = (s.x2 - s.x1) / (cycles * 2)
      let d = `M ${s.x1} ${s.y1}`
      for (let i = 0; i < cycles * 2; i++) {
        const cx = s.x1 + dx * (i + 0.5)
        const cy = s.y1 + (i % 2 === 0 ? -amp : amp)
        const ex = s.x1 + dx * (i + 1)
        d += ` Q ${cx} ${cy} ${ex} ${s.y1}`
      }
      return <path d={d} fill="none" stroke="currentColor" strokeWidth="2" />
    }

    case 'battery': {
      const midY = s.y + s.h / 2
      return (
        <g stroke="currentColor" strokeWidth="2" fill="none">
          <line x1={s.x} y1={s.y} x2={s.x} y2={s.y + s.h} />
          <line x1={s.x + s.w * 0.4} y1={midY - s.h * 0.35} x2={s.x + s.w * 0.4} y2={midY + s.h * 0.35} />
          <line x1={s.x + s.w * 0.6} y1={midY - s.h * 0.15} x2={s.x + s.w * 0.6} y2={midY + s.h * 0.15} />
          <line x1={s.x + s.w} y1={s.y} x2={s.x + s.w} y2={s.y + s.h} />
        </g>
      )
    }

    case 'label':
      return <text x={s.x} y={s.y} fontSize="14" fill="currentColor">{s.text}</text>

    default:
      return null
  }
}

export default function SketchDiagram({ sketch }) {
  const filterId = useId()
  const shapes = sketch && Array.isArray(sketch.shapes) ? sketch.shapes : null
  if (!shapes || shapes.length === 0) return null
  return (
    <svg viewBox={sketch.viewBox || DEFAULT_VIEWBOX} className="w-full h-auto text-white/80"
      style={{ filter: `url(#${filterId})` }}>
      <defs>
        <filter id={filterId} x="-10%" y="-10%" width="120%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="3" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="4" xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
      {shapes.map((s, i) => <Shape key={i} shape={s} />)}
    </svg>
  )
}
