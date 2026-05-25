import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import PageHeader from '../components/PageHeader'
import ModeBadge from '../components/ModeBadge'
import BottomNav from '../components/BottomNav'

const MODE_DESCRIPTIONS = {
  text:   'Strukturált magyarázat — lépésről lépésre',
  story:  'Ugyanaz az anyag élményszámba menő narratívában',
  visual: 'Térképek, diagramok, idővonalak magyarázattal',
  quiz:   '4 kérdés az anyag ellenőrzéséhez',
}

const MODE_ORDER = ['text', 'story', 'visual', 'quiz']

export default function TopicDetailPage() {
  const { subjectId, topicId } = useParams()
  const navigate = useNavigate()
  const [topic, setTopic] = useState(null)
  const [lessons, setLessons] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [t, l] = await Promise.all([
          api.curriculum.topic(topicId),
          api.lessons.forTopic(topicId),
        ])
        setTopic(t)
        setLessons(l)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [topicId])

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés...</div>
  }

  const activeByMode = Object.fromEntries(lessons.map(l => [l.mode, l]))

  return (
    <div className="pb-24">
      <PageHeader
        title={topic?.title_hu ?? ''}
        subtitle={topic?.nat_id}
        backTo={`/subjects/${subjectId}/topics`}
      />

      <div className="px-4 py-5 max-w-lg mx-auto">
        {/* Topic info */}
        <div className="card p-4 mb-5">
          <p className="text-slate-500 text-sm italic">{topic?.title}</p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            <span className="text-xs bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">
              {topic?.grade}. osztály
            </span>
            <span className="text-xs bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">
              {topic?.semester}. félév
            </span>
          </div>
        </div>

        {/* Mode cards */}
        <h2 className="font-bold text-slate-800 mb-3">Tanulási módok</h2>

        {lessons.length === 0 ? (
          <div className="card p-8 text-center text-slate-400">
            <div className="text-4xl mb-2">🚧</div>
            <p>Ehhez a témához még nincs jóváhagyott lecke.</p>
            <p className="text-sm mt-1">Hamarosan!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {MODE_ORDER.map(mode => {
              const lesson = activeByMode[mode]
              if (!lesson) return null
              return (
                <button
                  key={mode}
                  onClick={() => navigate(
                    mode === 'quiz'
                      ? `/lessons/${lesson.id}/quiz`
                      : `/lessons/${lesson.id}`
                  )}
                  className="card w-full p-4 text-left active:scale-[0.98] transition-transform"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <ModeBadge mode={mode} size="lg" />
                      <p className="text-sm text-slate-500 mt-1.5">{MODE_DESCRIPTIONS[mode]}</p>
                      {lesson.reading_time_minutes && (
                        <p className="text-xs text-slate-400 mt-1">
                          ⏱ kb. {lesson.reading_time_minutes} perc
                        </p>
                      )}
                    </div>
                    <span className="text-slate-300 text-xl">›</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      <BottomNav />
    </div>
  )
}
