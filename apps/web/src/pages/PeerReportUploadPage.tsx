import { Alert, Button, Card, Form, Input, InputNumber, Select, Space, Spin, Table, Typography, Upload, message } from 'antd';
import type { UploadFile } from 'antd';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { listEnterprises, listProjects } from '../services/enterpriseProject';
import type { Enterprise, Project } from '../services/enterpriseProject';
import { listProjectPeers } from '../services/peer';
import type { PeerCompany } from '../services/peer';
import { createPeerReport, listPeerReports, startPeerReportParse, uploadPeerReportFile } from '../services/peerReports';
import type { PeerReport } from '../services/peerReports';
import { useAuthStore } from '../stores/authStore';

interface UploadFormValues {
  peer_company_id: string;
  report_year: number;
  report_name?: string;
  upload?: { fileList: UploadFile[] };
}

export function PeerReportUploadPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const [loading, setLoading] = useState(Boolean(accessToken));
  const [error, setError] = useState<string | null>(null);
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [peers, setPeers] = useState<PeerCompany[]>([]);
  const [reports, setReports] = useState<PeerReport[]>([]);
  const [enterpriseId, setEnterpriseId] = useState<string>();
  const [projectId, setProjectId] = useState<string>();
  const [form] = Form.useForm<UploadFormValues>();

  const loadReports = async (nextProjectId = projectId) => {
    if (!accessToken || !nextProjectId) return;
    const [peerPage, reportPage] = await Promise.all([listProjectPeers(accessToken, nextProjectId), listPeerReports(accessToken, nextProjectId)]);
    setPeers(peerPage.items.filter((peer) => peer.confirmed_at));
    setReports(reportPage.items);
  };

  const refreshContext = async (nextEnterpriseId?: string, nextProjectId?: string) => {
    if (!accessToken) return;
    const enterprisePage = await listEnterprises(accessToken);
    const resolvedEnterpriseId = nextEnterpriseId ?? enterprisePage.items[0]?.enterprise_id;
    setEnterprises(enterprisePage.items);
    setEnterpriseId(resolvedEnterpriseId);
    if (resolvedEnterpriseId) {
      const projectPage = await listProjects(accessToken, resolvedEnterpriseId);
      const resolvedProjectId = nextProjectId ?? projectPage.items[0]?.project_id;
      setProjects(projectPage.items);
      setProjectId(resolvedProjectId);
      if (resolvedProjectId) await loadReports(resolvedProjectId);
    }
  };

  useEffect(() => {
    if (!accessToken) return;
    refreshContext().catch((err: unknown) => setError(err instanceof Error ? err.message : 'REQUEST_FAILED')).finally(() => setLoading(false));
  }, [accessToken]);

  const handleSubmit = async (values: UploadFormValues) => {
    if (!accessToken || !enterpriseId || !projectId) return;
    const uploadFile = values.upload?.fileList?.[0]?.originFileObj;
    if (!uploadFile) {
      message.error('请选择PDF文件');
      return;
    }
    const file = await uploadPeerReportFile(accessToken, { file: uploadFile, enterprise_id: enterpriseId, project_id: projectId });
    const report = await createPeerReport(accessToken, projectId, { peer_company_id: values.peer_company_id, file_id: file.file_id, report_year: values.report_year, report_name: values.report_name, report_language: 'zh' });
    const job = await startPeerReportParse(accessToken, projectId, report.peer_report_id);
    message.success(`解析任务已创建：${job.job_id}`);
    form.resetFields();
    await loadReports(projectId);
  };

  const handleParse = async (record: PeerReport) => {
    if (!accessToken || !projectId) return;
    const job = await startPeerReportParse(accessToken, projectId, record.peer_report_id);
    message.success(`解析任务已创建：${job.job_id}`);
    await loadReports(projectId);
  };

  if (!accessToken) return <Navigate to="/login" replace />;
  if (loading) return <main style={{ padding: 24 }}><Spin /></main>;
  if (error) return <main style={{ padding: 24 }}><Alert type="error" message="加载同行报告失败" description={error} /></main>;

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card extra={<Link to="/workbench">返回工作台</Link>}>
          <Typography.Title level={2}>同行报告上传与解析任务</Typography.Title>
          <Typography.Paragraph type="secondary">上传已确认同行的PDF ESG报告，创建解析任务并跟踪状态。</Typography.Paragraph>
        </Card>
        <Card title="项目上下文">
          <Space wrap>
            <Select style={{ width: 280 }} value={enterpriseId} options={enterprises.map((item) => ({ value: item.enterprise_id, label: item.enterprise_name }))} onChange={(value) => refreshContext(value)} />
            <Select style={{ width: 320 }} value={projectId} options={projects.map((item) => ({ value: item.project_id, label: item.project_name }))} onChange={(value) => { setProjectId(value); void loadReports(value); }} />
          </Space>
        </Card>
        <Card title="上传同行报告">
          <Form form={form} layout="inline" onFinish={handleSubmit} initialValues={{ report_year: new Date().getFullYear() }}>
            <Form.Item name="peer_company_id" rules={[{ required: true, message: '请选择已确认同行' }]}><Select style={{ width: 260 }} placeholder="已确认同行" options={peers.map((peer) => ({ value: peer.profile_peer_company_id ?? peer.peer_company_id, label: peer.company_name }))} /></Form.Item>
            <Form.Item name="report_year" rules={[{ required: true, message: '请输入报告年度' }]}><InputNumber min={2000} max={new Date().getFullYear() + 1} /></Form.Item>
            <Form.Item name="report_name"><Input placeholder="报告名称" /></Form.Item>
            <Form.Item name="upload" valuePropName="file" getValueFromEvent={(event) => event}><Upload beforeUpload={() => false} maxCount={1} accept="application/pdf"><Button>选择PDF</Button></Upload></Form.Item>
            <Button htmlType="submit" type="primary">上传并创建解析任务</Button>
          </Form>
        </Card>
        <Card title="同行报告记录">
          <Table rowKey="peer_report_id" dataSource={reports} pagination={false} columns={[
            { title: '报告', dataIndex: 'report_name' },
            { title: '年度', dataIndex: 'report_year' },
            { title: '状态', dataIndex: 'parse_status' },
            { title: '操作', render: (_: unknown, record: PeerReport) => <Button type="link" onClick={() => handleParse(record)}>重新解析</Button> },
          ]} />
        </Card>
      </Space>
    </main>
  );
}
