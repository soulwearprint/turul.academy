/**
 * Turul companion — evolution stages & customization.
 *
 * The mascot is a central product feature: it grows with the student from
 * Grade 5 to graduation. This module holds the (frontend) logic for that.
 *
 * NOTE: customization currently persists to localStorage. Moving it to the
 * user profile (server-side metadata) is a planned follow-up.
 */

// ── Evolution stages (from the design doc) ───────────────────────────────
export const STAGES = [
  { key: 'explorer',   minGrade: 5,  maxGrade: 6,  name: { hu: 'Felfedező',  en: 'Explorer'   }, accessory: 'none' },
  { key: 'adventurer', minGrade: 7,  maxGrade: 8,  name: { hu: 'Kalandor',   en: 'Adventurer' }, accessory: 'backpack' },
  { key: 'scholar',    minGrade: 9,  maxGrade: 10, name: { hu: 'Tudós',      en: 'Scholar'    }, accessory: 'glasses' },
  { key: 'mentor',     minGrade: 11, maxGrade: 12, name: { hu: 'Mentor',     en: 'Mentor'     }, accessory: 'cap' },
]

export function stageForGrade(grade = 7) {
  return STAGES.find(s => grade >= s.minGrade && grade <= s.maxGrade) ?? STAGES[1]
}

export function stageIndex(grade = 7) {
  return Math.max(0, STAGES.findIndex(s => grade >= s.minGrade && grade <= s.maxGrade))
}

// ── Customization options ─────────────────────────────────────────────────
export const COLOR_OPTIONS = ['blue', 'green', 'purple', 'gold']
export const ACCESSORY_OPTIONS = ['none', 'glasses', 'headphones', 'cap']

const STORE_KEY = 'turul_companion'

const DEFAULT_CONFIG = { color: 'blue', accessory: 'none' }

export function getTurulConfig() {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (!raw) return { ...DEFAULT_CONFIG }
    return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_CONFIG }
  }
}

export function setTurulConfig(patch) {
  const next = { ...getTurulConfig(), ...patch }
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(next))
    window.dispatchEvent(new CustomEvent('turul-config-changed', { detail: next }))
  } catch { /* ignore */ }
  return next
}
