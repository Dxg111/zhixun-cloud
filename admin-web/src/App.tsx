import { Navigate, Route, Routes } from 'react-router-dom'
import RequireAuth from './components/RequireAuth'
import AdminLayout from './layouts/AdminLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import OrgPage from './pages/OrgPage'
import JoinRequestsPage from './pages/JoinRequestsPage'
import KnowledgePage from './pages/KnowledgePage'
import QuestionsPage from './pages/QuestionsPage'
import CardsPage from './pages/CardsPage'
import ExamsPage from './pages/ExamsPage'
import ExportsPage from './pages/ExportsPage'
import SettingsPage from './pages/SettingsPage'
import AdminUsersPage from './pages/AdminUsersPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/org" element={<OrgPage />} />
        <Route path="/join-requests" element={<JoinRequestsPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/questions" element={<QuestionsPage />} />
        <Route path="/cards" element={<CardsPage />} />
        <Route path="/exams" element={<ExamsPage />} />
        <Route path="/exports" element={<ExportsPage />} />
        <Route path="/admins" element={<AdminUsersPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
