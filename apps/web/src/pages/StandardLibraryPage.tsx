import { Alert, Button, Card, Col, Descriptions, Form, Input, List, Row, Select, Space, Spin, Table, Tabs, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { listClauses, listMetrics, listStandardTopics, listStandards, listTopicMetrics, listTopics, getStandard } from '../services/standardLibrary';
import type { Metric, Standard, StandardClause, StandardTopicMap, Topic, TopicMetricMap } from '../services/standardLibrary';
import { useAuthStore } from '../stores/authStore';

export function StandardLibraryPage() {
  const token = useAuthStore((state) => state.accessToken);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState<string | null>(null);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [selectedStandard, setSelectedStandard] = useState<Standard | null>(null);
  const [clauses, setClauses] = useState<StandardClause[]>([]);
  const [standardTopics, setStandardTopics] = useState<StandardTopicMap[]>([]);
  const [topicMetrics, setTopicMetrics] = useState<TopicMetricMap[]>([]);

  const refresh = async () => {
    if (!token) return;
    setLoading(true);
    const [standardPage, topicPage, metricPage] = await Promise.all([listStandards(token), listTopics(token), listMetrics(token)]);
    setStandards(standardPage.items);
    setTopics(topicPage.items);
    setMetrics(metricPage.items);
    setLoading(false);
  };

  useEffect(() => { refresh().catch((err: unknown) => { setError(err instanceof Error ? err.message : 'REQUEST_FAILED'); setLoading(false); }); }, [token]);

  const openStandard = async (standardCode: string) => {
    if (!token) return;
    const standard = await getStandard(token, standardCode);
    setSelectedStandard(standard);
    const currentVersion = standard.versions?.find((item) => item.is_current) ?? standard.versions?.[0];
    if (currentVersion) {
      const [clausePage, topicMapPage] = await Promise.all([listClauses(token, standard.standard_code, currentVersion.standard_version_code), listStandardTopics(token, standard.standard_code, currentVersion.standard_version_code)]);
      setClauses(clausePage.items);
      setStandardTopics(topicMapPage.items);
    } else {
      setClauses([]);
      setStandardTopics([]);
    }
  };

  const openTopicMetrics = async (topicCode: string) => {
    if (!token) return;
    setTopicMetrics((await listTopicMetrics(token, topicCode)).metrics);
  };

  if (!token) return <Navigate to="/login" replace />;
  if (loading) return <main style={{ padding: 24 }}><Spin /></main>;
  if (error) return <main style={{ padding: 24 }}><Alert type="error" message="加载标准库失败" description={error} /></main>;

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card extra={<Link to="/workbench">返回工作台</Link>}>
          <Typography.Title level={2}>标准库、议题库与指标库</Typography.Title>
          <Typography.Paragraph type="secondary">查看公共标准与当前租户私有标准、标准条款、议题指标映射关系。</Typography.Paragraph>
        </Card>
        <Tabs items={[{
          key: 'standards', label: '标准库列表/详情', children: <Row gutter={16}><Col span={10}><Card title="标准列表"><Table rowKey="standard_code" size="small" dataSource={standards} pagination={false} columns={[{ title: '编码', dataIndex: 'standard_code' }, { title: '名称', dataIndex: 'standard_short_name' }, { title: '范围', dataIndex: 'scope_type', render: (value) => <Tag>{value}</Tag> }, { title: '操作', render: (_, record) => <Button type="link" onClick={() => openStandard(record.standard_code)}>查看</Button> }]} /></Card></Col><Col span={14}><Card title="标准详情与条款">{selectedStandard ? <Space direction="vertical" style={{ width: '100%' }}><Descriptions bordered size="small" column={1}><Descriptions.Item label="名称">{selectedStandard.standard_name}</Descriptions.Item><Descriptions.Item label="类型">{selectedStandard.standard_type}</Descriptions.Item><Descriptions.Item label="发布方">{selectedStandard.issuing_body ?? '-'}</Descriptions.Item><Descriptions.Item label="说明">{selectedStandard.description ?? '-'}</Descriptions.Item></Descriptions><List header="版本" dataSource={selectedStandard.versions ?? []} renderItem={(item) => <List.Item>{item.version_name}<Tag color={item.is_current ? 'green' : undefined}>{item.version_no}</Tag></List.Item>} /><Table rowKey="clause_code" size="small" dataSource={clauses} pagination={{ pageSize: 5 }} columns={[{ title: '条款号', dataIndex: 'clause_no' }, { title: '标题', dataIndex: 'clause_title' }, { title: '披露类型', dataIndex: 'disclosure_type' }, { title: '要求', dataIndex: 'is_required' }]} /></Space> : <Typography.Text type="secondary">请选择标准。</Typography.Text>}</Card></Col></Row>
        }, {
          key: 'topics', label: '议题库列表', children: <Card><Table rowKey="topic_code" dataSource={topics} columns={[{ title: '编码', dataIndex: 'topic_code' }, { title: '名称', dataIndex: 'topic_name' }, { title: '类别', dataIndex: 'topic_category', render: (value) => <Tag>{value}</Tag> }, { title: '说明', dataIndex: 'topic_description' }, { title: '指标映射', render: (_, record) => <Button type="link" onClick={() => openTopicMetrics(record.topic_code)}>查看推荐指标</Button> }]} /></Card>
        }, {
          key: 'metrics', label: '指标库列表', children: <Card><Table rowKey="metric_code" dataSource={metrics} columns={[{ title: '编码', dataIndex: 'metric_code' }, { title: '名称', dataIndex: 'metric_name' }, { title: '类型', dataIndex: 'metric_type' }, { title: '数据类型', dataIndex: 'data_type' }, { title: '单位', dataIndex: 'default_unit' }, { title: '必填', dataIndex: 'default_required', render: (value) => value ? <Tag color="red">是</Tag> : <Tag>否</Tag> }]} /></Card>
        }, {
          key: 'maps', label: '映射关系查看', children: <Row gutter={16}><Col span={12}><Card title="标准-议题映射"><Table rowKey="map_id" dataSource={standardTopics} pagination={false} columns={[{ title: '议题', dataIndex: 'topic_name' }, { title: '类别', dataIndex: 'topic_category' }, { title: '关键议题', dataIndex: 'is_key_topic', render: (value) => value ? <Tag color="green">是</Tag> : <Tag>否</Tag> }, { title: '相关条款', dataIndex: 'related_clause_codes', render: (value: string[]) => value?.join(', ') }]} /></Card></Col><Col span={12}><Card title="议题-指标映射"><Form layout="inline" style={{ marginBottom: 16 }}><Form.Item label="选择议题"><Select style={{ width: 260 }} options={topics.map((topic) => ({ value: topic.topic_code, label: `${topic.topic_code} ${topic.topic_name}` }))} onChange={openTopicMetrics} /></Form.Item></Form><Table rowKey="map_id" dataSource={topicMetrics} pagination={false} columns={[{ title: '指标', dataIndex: 'metric_name' }, { title: '类型', dataIndex: 'metric_type' }, { title: '必选', dataIndex: 'is_required', render: (value) => value ? <Tag color="red">是</Tag> : <Tag>否</Tag> }, { title: '默认选中', dataIndex: 'default_selected', render: (value) => value ? '是' : '否' }]} /></Card></Col></Row>
        }]} />
      </Space>
    </main>
  );
}
