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
  const { t } = useLang()
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
          return (
            <div key={subject.id} className="card p-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-brand-50 flex items-center justify-center text-2xl shrink-0">
                  {subjectIcon(subject.code)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold">{subject.name_hu}</div>
                  <div className="text-xs text-slate-500">{subject.grade_min}–{subject.grade_max}{t('subjects.grade.range')}</div>
                </div>
                {isEnrolled ? (
                  <button
                    onClick={() => navigate(usesNatModel(subject.code) ? natHref(subject) : `/subjects/${subject.id}/topics`)}
                    className="shrink-0 text-turul-blue text-sm font-semibold"
                  >
                    {t('subjects.open')}
                  </button>
                ) : (
                  <button
                    onClick={() => toggleEnrol(subject)}
                    disabled={enrolling === subject.id}
                    className="shrink-0 btn-primary text-sm py-2 px-3"
                  >
                    {enrolling === subject.id ? '...' : t('subjects.enrol')}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <BottomNav />
    </div>
  )
}
