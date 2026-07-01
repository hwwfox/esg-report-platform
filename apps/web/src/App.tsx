import { Spin } from 'antd';
import type { ReactElement } from 'react';
import { useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthApiError, getCurrentUser, refreshToken } from './services/auth';
import { LoginPage } from './pages/LoginPage';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { EnterpriseProjectPage } from './pages/EnterpriseProjectPage';
import { ForbiddenPage } from './pages/ForbiddenPage';
import { StandardLibraryPage } from './pages/StandardLibraryPage';
import { PeerAnalysisPage } from './pages/PeerAnalysisPage';
import { PeerReportUploadPage } from './pages/PeerReportUploadPage';
import { useAuthStore } from './stores/authStore';
import { hasAllPermissions } from './utils/permissions';

function ProtectedRoute({ children, permissions = [] }: { children: ReactElement; permissions?: string[] }) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const refreshTokenValue = useAuthStore((state) => state.refreshToken);
  const currentUser = useAuthStore((state) => state.currentUser);
  const setCurrentUser = useAuthStore((state) => state.setCurrentUser);
  const setTokens = useAuthStore((state) => state.setTokens);
  const logout = useAuthStore((state) => state.logout);
  const [isLoadingUser, setIsLoadingUser] = useState(Boolean(accessToken && !currentUser));

  useEffect(() => {
    if (!accessToken || currentUser) {
      setIsLoadingUser(false);
      return;
    }

    let isActive = true;

    const loadCurrentUser = async () => {
      try {
        const user = await getCurrentUser(accessToken);
        if (isActive) setCurrentUser(user);
      } catch (err) {
        if (err instanceof AuthApiError && err.code === 'AUTH_TOKEN_EXPIRED' && refreshTokenValue) {
          const tokens = await refreshToken(refreshTokenValue);
          if (!isActive) return;
          setTokens(tokens);
          const user = await getCurrentUser(tokens.access_token);
          if (isActive) setCurrentUser(user);
          return;
        }
        throw err;
      }
    };

    setIsLoadingUser(true);
    loadCurrentUser()
      .catch(() => {
        if (isActive) logout();
      })
      .finally(() => {
        if (isActive) setIsLoadingUser(false);
      });

    return () => {
      isActive = false;
    };
  }, [accessToken, currentUser, logout, refreshTokenValue, setCurrentUser, setTokens]);

  if (!accessToken) return <Navigate to="/login" replace />;
  if (isLoadingUser || !currentUser) return <main style={{ padding: 24 }}><Spin /></main>;
  if (permissions.length > 0 && !hasAllPermissions(currentUser.permissions, permissions)) return <Navigate to="/403" replace />;
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
      <Route path="/enterprise-projects" element={<ProtectedRoute><EnterpriseProjectPage /></ProtectedRoute>} />
      <Route path="/standard-library" element={<ProtectedRoute permissions={['standard:read', 'topic:read', 'metric:read']}><StandardLibraryPage /></ProtectedRoute>} />
      <Route path="/peer-analysis" element={<ProtectedRoute permissions={['project:read']}><PeerAnalysisPage /></ProtectedRoute>} />
      <Route path="/peer-reports" element={<ProtectedRoute permissions={['project:read']}><PeerReportUploadPage /></ProtectedRoute>} />
      <Route path="/403" element={<ForbiddenPage />} />
      <Route path="*" element={<Navigate to="/workbench" replace />} />
    </Routes>
  );
}
