import { Alert, Button, Card, Col, Descriptions, Form, Input, InputNumber, List, Row, Select, Space, Spin, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { getCurrentUser } from '../services/auth';
import { addProjectMember, createEnterprise, createProject, getProjectDashboard, listEnterprises, listProjectMembers, listProjects } from '../services/enterpriseProject';
import type { Enterprise, Project, ProjectMember } from '../services/enterpriseProject';
import { useAuthStore } from '../stores/authStore';

export function EnterpriseProjectPage() {
  const { accessToken, currentUser, setCurrentUser, logout } = useAuthStore();
  const [loading, setLoading] = useState(Boolean(accessToken));
  const [error, setError] = useState<string | null>(null);
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [selectedEnterpriseId, setSelectedEnterpriseId] = useState<string | undefined>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [projectForm] = Form.useForm();

  const refresh = async (enterpriseId?: string) => {
    if (!accessToken) return;
    const enterprisePage = await listEnterprises(accessToken);
    const nextEnterpriseId = enterpriseId ?? selectedEnterpriseId ?? enterprisePage.items[0]?.enterprise_id;
    setEnterprises(enterprisePage.items);
    setSelectedEnterpriseId(nextEnterpriseId);
    projectForm.setFieldsValue({ enterprise_id: nextEnterpriseId });
    const projectPage = await listProjects(accessToken, nextEnterpriseId);
    setProjects(projectPage.items);
  };

  useEffect(() => {
    if (!accessToken) return;
    (async () => {
      try {
        const user = currentUser ?? await getCurrentUser(accessToken);
        setCurrentUser(user);
        await refresh(user.current_enterprise_id ?? undefined);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'REQUEST_FAILED');
      } finally {
        setLoading(false);
      }
    })();
  }, [accessToken]);

  const handleEnterpriseCreate = async (values: { enterprise_name: string; enterprise_short_name?: string }) => {
    if (!accessToken) return;
    const enterprise = await createEnterprise(accessToken, values);
    message.success('企业已创建');
    await refresh(enterprise.enterprise_id);
  };

  const handleProjectCreate = async (values: { project_name: string; report_year: number; enterprise_id: string }) => {
    if (!accessToken || !currentUser) return;
    const project = await createProject(accessToken, { ...values, project_owner_user_id: currentUser.user_id, report_type: 'ESG', report_language: 'zh' });
    message.success('项目已创建');
    await refresh(project.enterprise_id);
    await openProject(project.project_id);
  };

  const openProject = async (projectId: string) => {
    if (!accessToken) return;
    const dashboard = await getProjectDashboard(accessToken, projectId);
    const memberPage = await listProjectMembers(accessToken, projectId);
    setSelectedProject(dashboard.project);
    setMembers(memberPage.items);
  };

  const handleAddSelf = async () => {
    if (!accessToken || !currentUser || !selectedProject) return;
    const memberPage = await addProjectMember(accessToken, selectedProject.project_id, currentUser);
    setMembers(memberPage.items);
    message.success('已添加项目成员');
  };

  if (!accessToken) return <Navigate to="/login" replace />;
  if (loading) return <main style={{ padding: 24 }}><Spin /></main>;
  if (error) return <main style={{ padding: 24 }}><Alert type="error" message="加载企业与项目失败" description={error} /></main>;

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card extra={<Button onClick={logout}>退出登录</Button>}>
          <Typography.Title level={2}>企业与报告项目</Typography.Title>
          <Typography.Paragraph type="secondary">选择企业、创建ESG报告项目，并在项目工作台中维护基础成员。</Typography.Paragraph>
        </Card>
        <Row gutter={16}>
          <Col span={8}>
            <Card title="企业列表/选择入口">
              <Select style={{ width: '100%', marginBottom: 16 }} placeholder="选择企业" value={selectedEnterpriseId} onChange={(value) => refresh(value)} options={enterprises.map((item) => ({ value: item.enterprise_id, label: item.enterprise_name }))} />
              <Form layout="vertical" onFinish={handleEnterpriseCreate}>
                <Form.Item name="enterprise_name" label="企业名称" rules={[{ required: true, message: '请输入企业名称' }]}><Input /></Form.Item>
                <Form.Item name="enterprise_short_name" label="企业简称"><Input /></Form.Item>
                <Button htmlType="submit" type="primary">创建企业</Button>
              </Form>
            </Card>
          </Col>
          <Col span={8}>
            <Card title="项目列表与创建">
              <Form form={projectForm} layout="vertical" onFinish={handleProjectCreate} initialValues={{ report_year: new Date().getFullYear() }}>
                <Form.Item name="enterprise_id" label="所属企业" rules={[{ required: true, message: '请选择企业' }]}><Select options={enterprises.map((item) => ({ value: item.enterprise_id, label: item.enterprise_name }))} /></Form.Item>
                <Form.Item name="project_name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}><Input /></Form.Item>
                <Form.Item name="report_year" label="报告年度" rules={[{ required: true, message: '请输入年度' }]}><InputNumber min={2000} max={new Date().getFullYear() + 1} style={{ width: '100%' }} /></Form.Item>
                <Button htmlType="submit" type="primary">创建项目</Button>
              </Form>
              <List style={{ marginTop: 16 }} dataSource={projects} renderItem={(item) => <List.Item actions={[<Button type="link" onClick={() => openProject(item.project_id)}>打开</Button>]}>{item.project_name} <Tag>{item.project_status}</Tag></List.Item>} />
            </Card>
          </Col>
          <Col span={8}>
            <Card title="项目详情/工作台">
              {selectedProject ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Descriptions bordered column={1} size="small">
                    <Descriptions.Item label="项目名称">{selectedProject.project_name}</Descriptions.Item>
                    <Descriptions.Item label="年度">{selectedProject.report_year}</Descriptions.Item>
                    <Descriptions.Item label="状态"><Tag color="blue">{selectedProject.project_status}</Tag></Descriptions.Item>
                    <Descriptions.Item label="负责人">{selectedProject.project_owner_user_id}</Descriptions.Item>
                  </Descriptions>
                  <Button onClick={handleAddSelf}>添加当前用户为成员</Button>
                  <List header="项目成员" dataSource={members} renderItem={(member) => <List.Item>{member.name}（{member.project_role}）<Tag>{member.status}</Tag></List.Item>} />
                </Space>
              ) : <Typography.Text type="secondary">请从项目列表打开一个项目。</Typography.Text>}
            </Card>
          </Col>
        </Row>
      </Space>
    </main>
  );
}
