// Subjects whose content lives in the 3-tier NAT model (curriculum_lessons/content_blocks)
// and is served via /nat, as opposed to the legacy per-subject topic flow (/subjects/:id/topics).
const NAT_SUBJECT_CODES = ['HISTORY', 'PHYSICS']

export function usesNatModel(code) {
  return NAT_SUBJECT_CODES.some(c => code?.includes(c))
}

export function natHref(subject) {
  return `/nat?subject=${subject.id}`
}

// Every NAT row (subject/topic/lesson) carries a Hungarian title_hu plus an English
// title — pick the one matching the active language, falling back to Hungarian since
// not every row is guaranteed a filled-in English title.
export function natTitle(row, lang) {
  return (lang === 'en' ? row?.title : row?.title_hu) ?? row?.title_hu ?? row?.title ?? ''
}

export function lessonCountLabel(t, n) {
  return t(n === 1 ? 'nat.lesson.count.one' : 'nat.lesson.count.other', { n })
}
