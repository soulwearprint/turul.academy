// Badge catalogue — display order + icon. Thresholds live in backend/core/badges.py
// (keep the type keys in sync); names/descriptions are i18n keys badge.<type>.name/.desc.
export const BADGES = [
  { type: 'first_lesson', icon: '🌱' },
  { type: 'lessons_10',   icon: '📚' },
  { type: 'lessons_25',   icon: '🏛️' },
  { type: 'perfect_quiz', icon: '🎯' },
  { type: 'perfect_5',    icon: '💎' },
  { type: 'comeback',     icon: '💪' },
  { type: 'topic_master', icon: '🏆' },
  { type: 'polymath',     icon: '🧭' },
  { type: 'streak_3',     icon: '🔥' },
  { type: 'streak_7',     icon: '⚡' },
  { type: 'streak_30',    icon: '🌟' },
  { type: 'study_60',     icon: '⏱️' },
]

export const badgeIcon = (type) => BADGES.find(b => b.type === type)?.icon ?? '🏅'

// "45 mp" / "12 p" / "1 ó 5 p" (hu) — "45 s" / "12 min" / "1 h 5 min" (en)
export function fmtDuration(seconds, lang) {
  const s = Math.max(0, Math.round(seconds || 0))
  const en = lang === 'en'
  if (s < 60) return en ? `${s} s` : `${s} mp`
  const m = Math.round(s / 60)
  if (m < 60) return en ? `${m} min` : `${m} p`
  const h = Math.floor(m / 60)
  const rest = m % 60
  if (en) return rest ? `${h} h ${rest} min` : `${h} h`
  return rest ? `${h} ó ${rest} p` : `${h} ó`
}
