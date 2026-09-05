// Subjects whose content lives in the 3-tier NAT model (curriculum_lessons/content_blocks)
// and is served via /nat, as opposed to the legacy per-subject topic flow (/subjects/:id/topics).
const NAT_SUBJECT_CODES = ['HISTORY', 'PHYSICS']

export function usesNatModel(code) {
  return NAT_SUBJECT_CODES.some(c => code?.includes(c))
}

export function natHref(subject) {
  return `/nat?subject=${subject.id}`
}
