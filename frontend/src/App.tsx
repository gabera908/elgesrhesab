import { Navigate, Route, Routes } from "react-router-dom";

import MainLayout from "./components/MainLayout";
import { useAuth } from "./contexts/AuthContext";
import AccountsPage from "./pages/AccountsPage";
import AmericanJournalPage from "./pages/AmericanJournalPage";
import CashFlowPage from "./pages/CashFlowPage";
import DashboardPage from "./pages/DashboardPage";
import ExtraReportsPage from "./pages/ExtraReportsPage";
import FiscalYearsPage from "./pages/FiscalYearsPage";
import GeneralJournalPage from "./pages/GeneralJournalPage";
import IncomeStatementPage from "./pages/IncomeStatementPage";
import JournalEntriesPage from "./pages/JournalEntriesPage";
import LoginPage from "./pages/LoginPage";
import OpeningBalancePage from "./pages/OpeningBalancePage";
import PartnersPage from "./pages/PartnersPage";
import ProjectsPage from "./pages/ProjectsPage";
import RegisterPage from "./pages/RegisterPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import UsersPage from "./pages/UsersPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas">
        <div className="text-ink-muted">جاري التحميل...</div>
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout>
              <DashboardPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/accounts"
        element={
          <ProtectedRoute>
            <MainLayout>
              <AccountsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/entries"
        element={
          <ProtectedRoute>
            <MainLayout>
              <JournalEntriesPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ReportsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/income-statement"
        element={
          <ProtectedRoute>
            <MainLayout>
              <IncomeStatementPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/cash-flow"
        element={
          <ProtectedRoute>
            <MainLayout>
              <CashFlowPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/american-journal"
        element={
          <ProtectedRoute>
            <MainLayout>
              <AmericanJournalPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/general-journal"
        element={
          <ProtectedRoute>
            <MainLayout>
              <GeneralJournalPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/partners"
        element={
          <ProtectedRoute>
            <MainLayout>
              <PartnersPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ProjectsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/fiscal"
        element={
          <ProtectedRoute>
            <MainLayout>
              <FiscalYearsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute>
            <MainLayout>
              <UsersPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/extra"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ExtraReportsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <MainLayout>
              <SettingsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings/opening-balance"
        element={
          <ProtectedRoute>
            <MainLayout>
              <OpeningBalancePage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}