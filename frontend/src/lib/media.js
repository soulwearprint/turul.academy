// Lesson images live in the public Supabase Storage bucket `content-media`. Cards store the
// storage path ("content-media/hist/…"), not a full URL, so a project move doesn't break them.
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL

export function mediaUrl(src) {
  if (!src) return null
  return /^https?:\/\//.test(src) ? src : `${SUPABASE_URL}/storage/v1/object/public/${src}`
}
