import { Alert, Button, Card, Descriptions, Spin, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthApiError, getCurrentUser, logoutRequest, refreshToken } from '../services/auth';
import { useAuthStore } from '../stores/authStore';

export function WorkbenchPage() {
  const { accessToken, refreshToken: refreshTokenValue, currentUser, setCurrentUser, setTokens, logout } = useAuthStore();
  const [loading, setLoading] = useState(Boolean(accessToken && !currentUser));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || currentUser) return;
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

    loadCurrentUser()
      .catch((err: unknown) => {
        if (!isActive) return;
        setError(err instanceof AuthApiError ? err.code : 'AUTH_UNAUTHORIZED');
        logout();
      })
      .finally(() => {
        if (isActive) setLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [accessToken, currentUser, logout, refreshTokenValue, setCurrentUser, setTokens]);

  const handleLogout = async () => {
    if (!accessToken) {
      logout();
      return;
    }
    try {
      await logoutRequest(accessToken);
    } finally {
      logout();
    }
  };

  if (!accessToken && !error) return <Navigate to="/login" replace />;
  if (loading) return <main style={{ padding: 24 }}><Spin /></main>;
  if (error) return <main style={{ padding: 24 }}><Alert type="error" message="登录状态失效或无权限" description={error} /></main>;

  return (
    <main style={{ padding: 24 }}>
      <Card extra={<Button onClick={handleLogout}>退出登录</Button>}>
        <Typography.Title level={2}>工作台</Typography.Title>
        {currentUser && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="用户">{currentUser.name}（{currentUser.email}）</Descriptions.Item>
            <Descriptions.Item label="租户">{currentUser.current_tenant_id}</Descriptions.Item>
            <Descriptions.Item label="角色">{currentUser.roles.join(', ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="权限">{currentUser.permissions.join(', ') || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>
    </main>
  );
}
