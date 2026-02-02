import { Routes, Route, Navigate } from 'react-router-dom'
import { RequireAuth } from '@/contexts/AuthContext'
import { AppLayout } from '@/components/layout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { TrendsPage } from '@/pages/TrendsPage'
import { AlertsPage } from '@/pages/AlertsPage'
import { CorrelationsPage } from '@/pages/CorrelationsPage'
import { BriefingPage } from '@/pages/BriefingPage'
import { IntegrationsPage } from '@/pages/IntegrationsPage'
import { MockDataPage } from '@/pages/MockDataPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { DataEntryPage } from '@/pages/DataEntryPage'

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="trends" element={<TrendsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="correlations" element={<CorrelationsPage />} />
        <Route path="briefing" element={<BriefingPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="mock-data" element={<MockDataPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="add/:type" element={<DataEntryPage />} />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
