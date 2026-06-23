import type { ReactElement } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { EnterpriseProjectPage } from './pages/EnterpriseProjectPage';
import { ForbiddenPage } from './pages/ForbiddenPage';
import { StandardLibraryPage } from './pages/StandardLibraryPage';
import { useAuthStore } from './stores/authStore';

function ProtectedRoute({ children }: { children: ReactElement }) {
  const accessToken = useAuthStore((state) => state.accessToken);
  if (!accessToken) return <Navigate to="/login" replace />;
  return children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/workbench" element={<WorkbenchPage />} />
      <Route path="/enterprise-projects" element={<EnterpriseProjectPage />} />
      <Route path="/standard-library" element={<StandardLibraryPage />} />
      <Route path="/workbench" element={<ProtectedRoute><WorkbenchPage /></ProtectedRoute>} />
      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="*" element={<Navigate to="/workbench" replace />} />
    </Routes>
  );
}
