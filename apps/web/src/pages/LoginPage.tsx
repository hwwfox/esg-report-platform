import { Button, Card, Form, Input, Typography, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { login } from '../services/auth';
import { useAuthStore } from '../stores/authStore';

interface LoginFormValues {
  email: string;
  password: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);

  const handleFinish = async (values: LoginFormValues) => {
    try {
      const session = await login(values.email, values.password);
      setSession(session);
      message.success('登录成功');
      navigate('/workbench');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '登录失败');
    }
  };

  return (
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#f5f7fb' }}>
      <Card style={{ width: 420 }}>
        <Typography.Title level={3}>ESG报告平台登录</Typography.Title>
        <Form layout="vertical" onFinish={handleFinish} initialValues={{ email: 'admin@example.com' }}>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}>
            <Input autoComplete="email" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>登录</Button>
        </Form>
        <Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>
          演示账号默认密码：ChangeMe123!
        </Typography.Paragraph>
      </Card>
    </main>
  );
}
