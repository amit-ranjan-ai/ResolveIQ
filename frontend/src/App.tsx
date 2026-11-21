

import { Navigate, Route, Routes } from "react-router-dom"

import { AppLayout } from "@/components/layout/app-layout"
import { Dashboard } from "@/pages/dashboard"
import { Tickets } from "@/pages/tickets"
import { KnowledgeBase } from "@/pages/knowledge-base"
import { UsersPage } from "@/pages/users"
import { Reports } from "@/pages/reports"
import { SettingsPage } from "@/pages/settings"

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tickets" element={<Tickets />} />
        <Route path="/knowledge-base" element={<KnowledgeBase />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}

export default App

