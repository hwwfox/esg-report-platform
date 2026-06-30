import { Alert, Button, Card, Checkbox, Form, Input, List, Select, Space, Spin, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { listEnterprises, listProjects } from '../services/enterpriseProject';
import type { Enterprise, Project } from '../services/enterpriseProject';
import { addPeerCompany, confirmGics, confirmPeerPool, getCurrentGics, identifyGics, listProjectPeers, recommendPeers, removeProjectPeer, searchPeerCompanies } from '../services/peer';
import type { GicsClassification, PeerCompany } from '../services/peer';
import { useAuthStore } from '../stores/authStore';

export function PeerAnalysisPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const [loading, setLoading] = useState(Boolean(accessToken));
  const [error, setError] = useState<string | null>(null);
  const [enterprises, setEnterprises] = useState<Enterprise[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [enterpriseId, setEnterpriseId] = useState<string>();
  const [projectId, setProjectId] = useState<string>();
  const [currentGics, setCurrentGics] = useState<GicsClassification | null>(null);
  const [candidates, setCandidates] = useState<GicsClassification[]>([]);
  const [peers, setPeers] = useState<PeerCompany[]>([]);
  const [selectedPeerIds, setSelectedPeerIds] = useState<string[]>([]);
  const [searchResults, setSearchResults] = useState<PeerCompany[]>([]);
  const [manualForm] = Form.useForm();
  const [searchForm] = Form.useForm();

  const loadPeers = async (nextProjectId = projectId) => {
    if (!accessToken || !nextProjectId) return;
    const page = await listProjectPeers(accessToken, nextProjectId);
    setPeers(page.items);
    setSelectedPeerIds(page.items.filter((item) => item.selected).map((item) => item.peer_company_id));
  };

  const refreshEnterpriseContext = async (nextEnterpriseId?: string, nextProjectId?: string) => {
    if (!accessToken) return;
    const enterprisePage = await listEnterprises(accessToken);
    const resolvedEnterpriseId = nextEnterpriseId ?? enterprisePage.items[0]?.enterprise_id;
    setEnterprises(enterprisePage.items);
    setEnterpriseId(resolvedEnterpriseId);
    if (resolvedEnterpriseId) {
      const projectPage = await listProjects(accessToken, resolvedEnterpriseId);
      setProjects(projectPage.items);
      const resolvedProjectId = nextProjectId ?? projectPage.items[0]?.project_id;
      setProjectId(resolvedProjectId);
      const gics = await getCurrentGics(accessToken, resolvedEnterpriseId);
      setCurrentGics(gics.current_gics);
      if (resolvedProjectId) await loadPeers(resolvedProjectId);
    }
  };

  useEffect(() => {
    if (!accessToken) return;
    refreshEnterpriseContext().catch((err: unknown) => setError(err instanceof Error ? err.message : 'REQUEST_FAILED')).finally(() => setLoading(false));
  }, [accessToken]);

  const handleIdentify = async () => {
    if (!accessToken || !enterpriseId) return;
    const result = await identifyGics(accessToken, enterpriseId);
    setCandidates([result.primary_result, ...result.alternative_results]);
    message.success('已生成GICS候选，请人工确认');
  };

  const handleConfirmGics = async (candidate: GicsClassification) => {
    if (!accessToken || !enterpriseId) return;
    const result = await confirmGics(accessToken, enterpriseId, candidate);
    setCurrentGics(result.current_gics);
    setCandidates([]);
    message.success('GICS已确认');
  };

  const handleRecommendPeers = async () => {
    if (!accessToken || !projectId) return;
    const result = await recommendPeers(accessToken, projectId);
    setPeers(result.recommended_peers);
    setSelectedPeerIds(result.recommended_peers.filter((item) => item.selected).map((item) => item.peer_company_id));
    message.success('同行推荐已生成');
  };

  const handleAddPeer = async (values: { company_name: string; stock_code?: string; exchange?: string; reason?: string }) => {
    if (!accessToken || !projectId) return;
    await addPeerCompany(accessToken, projectId, values);
    manualForm.resetFields();
    await loadPeers(projectId);
    message.success('已手动添加同行');
  };

  const handleSearchPeers = async (values: { keyword?: string }) => {
    if (!accessToken) return;
    const result = await searchPeerCompanies(accessToken, { keyword: values.keyword, gics_code: currentGics?.gics_code });
    setSearchResults(result.items);
    message.success('同行候选已更新');
  };

  const handleSelectSearchedPeer = async (peer: PeerCompany) => {
    if (!accessToken || !projectId) return;
    await addPeerCompany(accessToken, projectId, { peer_company_id: peer.profile_peer_company_id ?? peer.peer_company_id, company_name: peer.company_name, reason: '从同行候选库选择' });
    await loadPeers(projectId);
    message.success('已从候选库添加同行');
  };

  const handleRemovePeer = async (peer: PeerCompany) => {
    if (!accessToken || !projectId) return;
    await removeProjectPeer(accessToken, projectId, peer.peer_company_id);
    await loadPeers(projectId);
    message.success('已移除同行');
  };

  const handleConfirmPeerPool = async () => {
    if (!accessToken || !projectId) return;
    const result = await confirmPeerPool(accessToken, projectId, selectedPeerIds);
    setPeers(result.items);
    message.success(`同行池已确认：${result.confirmed_count} 家`);
  };

  if (!accessToken) return <Navigate to="/login" replace />;
  if (loading) return <main style={{ padding: 24 }}><Spin /></main>;
  if (error) return <main style={{ padding: 24 }}><Alert type="error" message="加载GICS与同行池失败" description={error} /></main>;

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card extra={<Link to="/workbench">返回工作台</Link>}>
          <Typography.Title level={2}>GICS识别与同行池</Typography.Title>
          <Typography.Paragraph type="secondary">确认企业GICS四级行业后，生成项目同行推荐并人工确认同行池。</Typography.Paragraph>
        </Card>
        <Card title="项目上下文">
          <Space wrap>
            <Select style={{ width: 280 }} value={enterpriseId} placeholder="选择企业" options={enterprises.map((item) => ({ value: item.enterprise_id, label: item.enterprise_name }))} onChange={(value) => refreshEnterpriseContext(value)} />
            <Select style={{ width: 320 }} value={projectId} placeholder="选择项目" options={projects.map((item) => ({ value: item.project_id, label: item.project_name }))} onChange={(value) => { setProjectId(value); void loadPeers(value); }} />
          </Space>
        </Card>
        <Card title="1. GICS候选与人工确认" extra={<Button type="primary" onClick={handleIdentify} disabled={!enterpriseId}>识别GICS候选</Button>}>
          {currentGics ? <Alert type="success" showIcon message={`当前已确认：${currentGics.gics_code} ${currentGics.gics_name_cn ?? currentGics.gics_name_en}`} /> : <Alert type="warning" showIcon message="尚未确认GICS，未确认时会阻断同行推荐。" />}
          <List style={{ marginTop: 16 }} dataSource={candidates} renderItem={(item) => (
            <List.Item actions={[<Button type="link" onClick={() => handleConfirmGics(item)}>确认此GICS</Button>]}>
              <List.Item.Meta title={`${item.gics_code} ${item.gics_name_cn ?? item.gics_name_en}`} description={`${item.reason ?? '-'} ${item.confidence ? `置信度 ${item.confidence}` : ''}`} />
            </List.Item>
          )} />
        </Card>
        <Card title="2. 同行推荐与手动添加" extra={<Button type="primary" onClick={handleRecommendPeers} disabled={!projectId}>生成同行推荐</Button>}>
          <Form form={searchForm} layout="inline" onFinish={handleSearchPeers} style={{ marginBottom: 16 }}>
            <Form.Item name="keyword"><Input placeholder="搜索候选库：公司/代码" /></Form.Item>
            <Button htmlType="submit">搜索候选库</Button>
          </Form>
          {searchResults.length > 0 && (
            <List style={{ marginBottom: 16 }} bordered dataSource={searchResults} renderItem={(item) => (
              <List.Item actions={[<Button type="link" onClick={() => handleSelectSearchedPeer(item)}>选择</Button>]}>
                <List.Item.Meta title={`${item.company_name} ${item.stock_code ?? ''}`} description={`${item.exchange ?? '-'} / ${item.gics_level_4_name ?? '-'}`} />
              </List.Item>
            )} />
          )}
          <Form form={manualForm} layout="inline" onFinish={handleAddPeer} style={{ marginBottom: 16 }}>
            <Form.Item name="company_name" rules={[{ required: true, message: '请输入公司名称' }]}><Input placeholder="同行公司名称" /></Form.Item>
            <Form.Item name="stock_code"><Input placeholder="股票代码" /></Form.Item>
            <Form.Item name="exchange"><Input placeholder="交易所" /></Form.Item>
            <Form.Item name="reason"><Input placeholder="添加原因" /></Form.Item>
            <Button htmlType="submit">手动添加</Button>
          </Form>
          <Table rowKey="peer_company_id" dataSource={peers} pagination={false} columns={[
            { title: '选择', render: (_: unknown, record: PeerCompany) => <Checkbox checked={selectedPeerIds.includes(record.peer_company_id)} onChange={(event) => setSelectedPeerIds((current) => event.target.checked ? [...new Set([...current, record.peer_company_id])] : current.filter((id) => id !== record.peer_company_id))} /> },
            { title: '公司', dataIndex: 'company_name' },
            { title: '代码', dataIndex: 'stock_code' },
            { title: '交易所', dataIndex: 'exchange' },
            { title: 'GICS', render: (_: unknown, record: PeerCompany) => record.gics_level_4_code ? `${record.gics_level_4_code} ${record.gics_level_4_name ?? ''}` : '-' },
            { title: '综合分', dataIndex: 'overall_score' },
            { title: '理由', dataIndex: 'recommendation_reason' },
            { title: '状态', render: (_: unknown, record: PeerCompany) => record.confirmed_at ? <Tag color="green">已确认</Tag> : record.selected ? <Tag color="blue">已选择</Tag> : <Tag>候选</Tag> },
            { title: '操作', render: (_: unknown, record: PeerCompany) => <Button danger type="link" onClick={() => handleRemovePeer(record)}>移除</Button> },
          ]} />
          <Button style={{ marginTop: 16 }} type="primary" onClick={handleConfirmPeerPool} disabled={!selectedPeerIds.length}>确认同行池</Button>
        </Card>
      </Space>
    </main>
  );
}
