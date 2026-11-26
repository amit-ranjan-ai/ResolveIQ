import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AnimatePresence } from "motion/react";

import { AppLayout } from "@/components/layout/app-layout";
import { AppLoader } from "@/components/layout/app-loader";
import { useAuth } from "@/contexts/auth-context";
import { LoginPage } from "@/pages/login";
import { Dashboard } from "@/pages/dashboard";
import { Tickets } from "@/pages/tickets";
import { KnowledgeBase } from "@/pages/knowledge-base";
import { UsersPage } from "@/pages/users";
import { Reports } from "@/pages/reports";
import { SettingsPage } from "@/pages/settings";

function App() {
  const { isLoading, isAuthenticated } = useAuth();
  const [showIntro, setShowIntro] = useState(true);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setShowIntro(false);
    }, 1400);

    return () => window.clearTimeout(timeout);
  }, []);

  if (isLoading || showIntro) {
    return (
      <AnimatePresence>
        <AppLoader key="app-loader" />
      </AnimatePresence>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/*"
        element={
          isAuthenticated ? (
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
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}

export default App;
