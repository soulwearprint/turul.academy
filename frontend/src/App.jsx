import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'

import LoginPage from './pages/LoginPage'
import OnboardingPage from './pages/OnboardingPage'
import HomePage from './pages/HomePage'
import SubjectsPage from './pages/SubjectsPage'
import TopicsPage from './pages/TopicsPage'
import TopicDetailPage from './pages/TopicDetailPage'
import LessonPage from './pages/LessonPage'
import QuizPage from './pages/QuizPage'
import ProgressPage from './pages/ProgressPage'

function RequireAuth({ children }) {
  const { session, loading } = useAuth()
  if (loading) return <div className="flex h-screen items-center justify-center text-slate-400">Betöltés...</div>
  if (!session) return <Navigate to="/login" replace />
  return children
}

function RedirectIfAuth({ children }) {
  const { session, loading } = useAuth()
  if (loading) return null
  if (session) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<RedirectIfAuth><LoginPage /></RedirectIfAuth>} />

          {/* Protected */}
          <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
          <Route path="/onboarding" element={<RequireAuth><OnboardingPage /></RequireAuth>} />
          <Route path="/subjects" element={<RequireAuth><SubjectsPage /></RequireAuth>} />
          <Route path="/subjects/:subjectId/topics" element={<RequireAuth><TopicsPage /></RequireAuth>} />
          <Route path="/subjects/:subjectId/topics/:topicId" element={<RequireAuth><TopicDetailPage /></RequireAuth>} />
          <Route path="/lessons/:lessonId" element={<RequireAuth><LessonPage /></RequireAuth>} />
          <Route path="/lessons/:lessonId/quiz" element={<RequireAuth><QuizPage /></RequireAuth>} />
          <Route path="/progress" element={<RequireAuth><ProgressPage /></RequireAuth>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
