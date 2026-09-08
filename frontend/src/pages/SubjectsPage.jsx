import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useLang } from '../contexts/LanguageContext'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import BottomNav from '../components/BottomNav'
import { usesNatModel, natHref } from '../lib/nat'

const SUBJECT_ICONS = {
  HISTORY: '🏛️',
  PHYSICS: '⚛️',
  MATH:    '📐',
  BIOLOGY: '🧬',
  CHEMISTRY: '🧪',
}

function subjectIcon(code) {
  for (const [key, icon] of Object.entries(SUBJECT_ICONS)) {
    if (code.includes(key)) return icon
  }
  return '📘'
}

export default function SubjectsPage() {
  const { session } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const [subjects, setSubjects]     = useState([])
  const [enrolled, setEnrolled]     = useState(new Set())
  const [loading, setLoading]       = useState(true)
  const [enrolling, setEnrolling]   = useState(null)

  const token = session?.access_token

  useEffect(() => {
    async function load() {
      const [all, my] = await Promise.all([
        api.curriculum.subjects(),
        api.account.subjects(token),
      ])
      setSubjects(all)
      setEnrolled(new Set(my.map(e => e.subject.id)))
      setLoading(false)
    }
    load()
  }, [token])

  async function toggleEnrol(subject) {
    if (enrolled.has(subject.id)) return // unenrol not implemented
    setEnrolling(subject.id)
    try {
      await api.account.enrol(subject.id, token)
      setEnrolled(prev => new Set([...prev, subject.id]))
    } finally {
      setEnrolling(null)
    }
  }

  return (
    <div className="pb-24">
      <PageHeader title={t('subjects.title')} subtitle={t('subjects.subtitle')} />

      <div className="px-4 py-5 max-w-lg mx-auto space-y-3">
        {loading ? (
          <div className="text-center text-slate-400 py-12">{t('common.loading')}</div>
        ) : subjects.map(subject => {
          const isEnrolled = enrolled.has(subject.id)
          const isEnrolling = enrolling === subject.id
          const name = (lang === 'en' ? subject.name : subject.name_hu) ?? subject.name_hu
          return (
            <button
              key={subject.id}
              onClick={() => isEnrolled
                ? navigate(usesNatModel(subject.code) ? natHref(subject) : `/subjects/${subject.id}/topics`)
                : toggleEnrol(subject)}
              disabled={isEnrolling}
              className="card w-full p-4 text-left active:scale-[0.98] transition-transform disabled:opacity-60"
            >
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center text-2xl shrink-0">
                  {subjectIcon(subject.code)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold">{name}</div>
                  <div className="text-xs text-slate-500">{subject.grade_min}–{subject.grade_max}{t('subjects.grade.range')}</div>
                </div>
                {isEnrolled ? (
                  <span className="shrink-0 text-turul-blue text-sm font-semibold">{t('subjects.open')}</span>
                ) : (
                  <span className="shrink-0 btn-primary text-sm py-2 px-3 pointer-events-none">
                    {isEnrolling ? '...' : t('subjects.enrol')}
                  </span>
                )}
              </div>
            </button>
          )
        })}
      </div>

      <BottomNav />
    </div>
  )
}
