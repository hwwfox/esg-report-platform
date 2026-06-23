import type { ReactElement } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { ForbiddenPage } from './pages/ForbiddenPage';
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
      <Route path="/workbench" element={<ProtectedRoute><WorkbenchPage /></ProtectedRoute>} />
      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="*" element={<Navigate to="/workbench" replace />} />
    </Routes>
  );
}
