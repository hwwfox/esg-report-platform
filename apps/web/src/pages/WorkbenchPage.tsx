import { Alert, Button, Card, Descriptions, Space, Spin, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { getCurrentUser } from '../services/auth';
import { useAuthStore } from '../stores/authStore';

export function WorkbenchPage() {
  const { accessToken, currentUser, setCurrentUser, logout } = useAuthStore();
  const [loading, setLoading] = useState(Boolean(accessToken && !currentUser));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken || currentUser) return;
    getCurrentUser(accessToken)
      .then(setCurrentUser)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'AUTH_UNAUTHORIZED');
        logout();
      })
      .finally(() => setLoading(false));
  }, [accessToken, currentUser, logout, setCurrentUser]);

  if (!accessToken && !error) return <Navigate to="/login" replace />;
  if (loading) return <main style={{ padding: 24 }}><Spin /></main>;
  if (error) return <main style={{ padding: 24 }}><Alert type="error" message="登录状态失效或无权限" description={error} /></main>;

  return (
    <main style={{ padding: 24 }}>
      <Card extra={<Space><Link to="/enterprise-projects">企业与项目</Link><Button onClick={logout}>退出登录</Button></Space>}>
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
