/**
 * TurulMascot — the geometric Turul companion.
 *
 * Design intent (from the product vision doc): minimalist, friendly, geometric,
 * modern, easy to animate. Never aggressive — no claws, weapons, military or
 * heraldic styling. The mascot reacts to the student's actions via `mood`.
 *
 * Props:
 *   mood      'idle' | 'happy' | 'celebrate' | 'thinking' | 'curious' | 'focused' | 'sleepy' | 'encouraging'
 *   color     'blue' | 'green' | 'purple' | 'gold'
 *   accessory 'none' | 'glasses' | 'headphones' | 'cap' | 'backpack'
 *   size      number (px, default 120)
 *   animate   boolean — idle float + blink (default true)
 *   shadow    boolean — soft ground shadow (default true)
 */

const PALETTE = {
  blue:   { base: '#2563EB', dark: '#1D4ED8', belly: '#DBEAFE', beak: '#F59E0B' },
  green:  { base: '#22C55E', dark: '#16A34A', belly: '#DCFCE7', beak: '#F59E0B' },
  purple: { base: '#8B5CF6', dark: '#7C3AED', belly: '#EDE9FE', beak: '#F59E0B' },
  gold:   { base: '#F59E0B', dark: '#D97706', belly: '#FEF3C7', beak: '#B45309' },
}

const INK = '#1E293B'

// Moods where eyes are "open" (round) → eligible for blink animation
const OPEN_EYE_MOODS = new Set(['idle', 'curious', 'focused', 'encouraging', 'thinking'])

function Eyes({ mood }) {
  // Closed / arc-style happy eyes
  if (mood === 'happy' || mood === 'celebrate') {
    return (
      <g stroke={INK} strokeWidth="6" strokeLinecap="round" fill="none">
        <path d="M68 112 Q82 99 96 112" />
        <path d="M104 112 Q118 99 132 112" />
      </g>
    )
  }
  if (mood === 'sleepy') {
    return (
      <g stroke={INK} strokeWidth="5.5" strokeLinecap="round" fill="none">
        <path d="M68 110 Q82 119 96 110" />
        <path d="M104 110 Q118 119 132 110" />
      </g>
    )
  }
  if (mood === 'focused') {
    // Narrowed, determined eyes
    return (
      <g fill={INK}>
        <rect x="68" y="108" width="28" height="9" rx="4.5" />
        <rect x="104" y="108" width="28" height="9" rx="4.5" />
      </g>
    )
  }

  // Round open eyes; pupils shift slightly per mood
  const look = mood === 'thinking' ? { dx: 4, dy: -3 } : mood === 'curious' ? { dx: 0, dy: -1 } : { dx: 0, dy: 0 }
  const pr = mood === 'curious' ? 8.5 : 7.5
  return (
    <g>
      <circle cx="82" cy="110" r="16" fill="#FFFFFF" />
      <circle cx="118" cy="110" r="16" fill="#FFFFFF" />
      <circle cx={82 + look.dx} cy={110 + look.dy} r={pr} fill={INK} />
      <circle cx={118 + look.dx} cy={110 + look.dy} r={pr} fill={INK} />
      <circle cx={79 + look.dx} cy={107 + look.dy} r="2.6" fill="#FFFFFF" />
      <circle cx={115 + look.dx} cy={107 + look.dy} r="2.6" fill="#FFFFFF" />
    </g>
  )
}

function Accessory({ accessory, c }) {
  switch (accessory) {
    case 'glasses':
      return (
        <g stroke={INK} strokeWidth="4" fill="none">
          <circle cx="82" cy="110" r="20" />
          <circle cx="118" cy="110" r="20" />
          <path d="M102 110 h-4 M138 104 q8 -2 10 4" strokeLinecap="round" />
        </g>
      )
    case 'headphones':
      return (
        <g>
          <path d="M48 96 a52 52 0 0 1 104 0" fill="none" stroke={INK} strokeWidth="7" strokeLinecap="round" />
          <rect x="38" y="92" width="20" height="34" rx="10" fill={INK} />
          <rect x="142" y="92" width="20" height="34" rx="10" fill={INK} />
        </g>
      )
    case 'cap':
      return (
        <g>
          <rect x="66" y="42" width="68" height="14" rx="4" fill={INK} transform="rotate(-3 100 49)" />
          <path d="M100 30 L150 46 L100 62 L50 46 Z" fill="#0F172A" />
          <path d="M148 47 l2 26" stroke="#0F172A" strokeWidth="3" strokeLinecap="round" />
          <circle cx="150" cy="75" r="4" fill={c.beak} />
        </g>
      )
    case 'backpack':
      return (
        <g>
          <path d="M58 150 q-16 4 -14 26 q14 8 26 4" fill={c.dark} />
          <rect x="40" y="156" width="20" height="22" rx="8" fill={c.dark} />
        </g>
      )
    default:
      return null
  }
}

function Sparkles() {
  return (
    <g fill="#F59E0B">
      <path d="M40 60 l3 8 l8 3 l-8 3 l-3 8 l-3 -8 l-8 -3 l8 -3 z" className="animate-sparkle" style={{ transformBox: 'fill-box', transformOrigin: 'center' }} />
      <path d="M162 78 l2.4 6 l6 2.4 l-6 2.4 l-2.4 6 l-2.4 -6 l-6 -2.4 l6 -2.4 z" className="animate-sparkle" style={{ transformBox: 'fill-box', transformOrigin: 'center', animationDelay: '0.5s' }} />
      <circle cx="150" cy="40" r="3.5" className="animate-sparkle" style={{ transformBox: 'fill-box', transformOrigin: 'center', animationDelay: '0.9s' }} />
    </g>
  )
}

export default function TurulMascot({
  mood = 'idle',
  color = 'blue',
  accessory = 'none',
  size = 120,
  animate = true,
  shadow = true,
  className = '',
}) {
  const c = PALETTE[color] ?? PALETTE.blue
  const canBlink = animate && OPEN_EYE_MOODS.has(mood)
  const tilt = mood === 'curious' ? -8 : 0

  return (
    <div
      className={`inline-block ${animate ? 'animate-float' : ''} ${className}`}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 200 210" width={size} height={size} role="img" aria-label="Turul">
        {shadow && <ellipse cx="100" cy="198" rx="48" ry="8" fill="#0F172A" opacity="0.08" />}

        <g transform={`rotate(${tilt} 100 120)`}>
          {/* Crest tufts */}
          <g fill={c.dark}>
            <ellipse cx="100" cy="42" rx="7" ry="17" />
            <ellipse cx="82"  cy="50" rx="6" ry="14" transform="rotate(-22 82 50)" />
            <ellipse cx="118" cy="50" rx="6" ry="14" transform="rotate(22 118 50)" />
          </g>

          {/* Wings (soft, rounded — peeking from behind) */}
          <ellipse cx="48"  cy="130" rx="17" ry="32" fill={c.dark} transform="rotate(18 48 130)" />
          <ellipse cx="152" cy="130" rx="17" ry="32" fill={c.dark} transform="rotate(-18 152 130)" />

          {/* Body */}
          <ellipse cx="100" cy="122" rx="62" ry="66" fill={c.base} />
          {/* Belly */}
          <ellipse cx="100" cy="134" rx="40" ry="46" fill={c.belly} />

          {/* Face */}
          <g
            className={canBlink ? 'animate-blink' : ''}
            style={canBlink ? { transformBox: 'fill-box', transformOrigin: 'center' } : undefined}
          >
            <Eyes mood={mood} />
          </g>

          {/* Beak — soft rounded diamond, never a hook */}
          <path d="M100 122 L111 132 L100 142 L89 132 Z" fill={c.beak} stroke={c.beak} strokeWidth="2" strokeLinejoin="round" />

          <Accessory accessory={accessory} c={c} />
        </g>

        {mood === 'celebrate' && <Sparkles />}
      </svg>
    </div>
  )
}
