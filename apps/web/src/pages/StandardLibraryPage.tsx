import { Alert, Button, Card, Col, Form, Input, Row, Select, Space, Spin, Table, Tabs, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { getRecommendedMetrics, listMetrics, listStandards, listTopics } from '../services/standardLibrary';
import type { Metric, Standard, Topic } from '../services/standardLibrary';
import { useAuthStore } from '../stores/authStore';

export function StandardLibraryPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const [loading, setLoading] = useState(Boolean(accessToken));
  const [error, setError] = useState<string | null>(null);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [recommendedMetrics, setRecommendedMetrics] = useState<Metric[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);

  const refreshAll = async () => {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    try {
      const [standardPage, topicPage, metricPage] = await Promise.all([
        listStandards(accessToken),
        listTopics(accessToken),
        listMetrics(accessToken),
      ]);
      setStandards(standardPage.items);
      setTopics(topicPage.items);
      setMetrics(metricPage.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'REQUEST_FAILED');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshAll();
  }, [accessToken]);

  const handleStandardSearch = async (values: { keyword?: string; standard_type?: string; applicable_market?: string }) => {
    if (!accessToken) return;
    const page = await listStandards(accessToken, values);
    setStandards(page.items);
    message.success('标准列表已更新');
  };

  const handleTopicSearch = async (values: { keyword?: string; topic_category?: string }) => {
    if (!accessToken) return;
    const page = await listTopics(accessToken, values);
    setTopics(page.items);
    message.success('议题列表已更新');
  };

  const handleMetricSearch = async (values: { keyword?: string; metric_type?: string; topic_code?: string }) => {
    if (!accessToken) return;
    const page = await listMetrics(accessToken, values);
    setMetrics(page.items);
    message.success('指标列表已更新');
  };

  const openRecommendedMetrics = async (topic: Topic) => {
    if (!accessToken) return;
    const response = await getRecommendedMetrics(accessToken, topic.topic_code);
    setSelectedTopic(topic);
    setRecommendedMetrics(response.metrics);
  };

  if (!accessToken) return <Navigate to="/login" replace />;
  if (loading) return <main style={{ padding: 24 }}><Spin /></main>;
  if (error) return <main style={{ padding: 24 }}><Alert type="error" message="加载标准库失败" description={error} /></main>;

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card extra={<Link to="/workbench">返回工作台</Link>}>
          <Typography.Title level={2}>标准库 / 议题库 / 指标库</Typography.Title>
          <Typography.Paragraph type="secondary">查看平台公共与租户私有的ESG标准、议题、指标及推荐指标映射。</Typography.Paragraph>
        </Card>
        <Tabs
          items={[
            {
              key: 'standards',
              label: '标准库',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Card>
                    <Form layout="inline" onFinish={handleStandardSearch}>
                      <Form.Item name="keyword" label="关键词"><Input allowClear placeholder="标准编码/名称" /></Form.Item>
                      <Form.Item name="standard_type" label="类型"><Input allowClear placeholder="voluntary" /></Form.Item>
                      <Form.Item name="applicable_market" label="市场"><Input allowClear placeholder="global / A_share" /></Form.Item>
                      <Button htmlType="submit" type="primary">查询</Button>
                    </Form>
                  </Card>
                  <Table rowKey="standard_code" dataSource={standards} pagination={{ pageSize: 10 }} columns={[
                    { title: '编码', dataIndex: 'standard_code' },
                    { title: '名称', dataIndex: 'standard_name' },
                    { title: '简称', dataIndex: 'standard_short_name' },
                    { title: '类型', dataIndex: 'standard_type' },
                    { title: '适用市场', dataIndex: 'applicable_market' },
                    { title: '当前版本', dataIndex: 'current_version' },
                    { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color="green">{value}</Tag> },
                  ]} />
                </Space>
              ),
            },
            {
              key: 'topics',
              label: '议题库',
              children: (
                <Row gutter={16}>
                  <Col span={16}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Card>
                        <Form layout="inline" onFinish={handleTopicSearch}>
                          <Form.Item name="keyword" label="关键词"><Input allowClear placeholder="议题编码/名称" /></Form.Item>
                          <Form.Item name="topic_category" label="类别"><Select allowClear style={{ width: 120 }} options={[{ value: 'E', label: 'E' }, { value: 'S', label: 'S' }, { value: 'G', label: 'G' }]} /></Form.Item>
                          <Button htmlType="submit" type="primary">查询</Button>
                        </Form>
                      </Card>
                      <Table rowKey="topic_code" dataSource={topics} pagination={{ pageSize: 10 }} columns={[
                        { title: '编码', dataIndex: 'topic_code' },
                        { title: '名称', dataIndex: 'topic_name' },
                        { title: '类别', dataIndex: 'topic_category', render: (value: string) => <Tag>{value}</Tag> },
                        { title: '财务重要性', dataIndex: 'default_financial_materiality' },
                        { title: '影响重要性', dataIndex: 'default_impact_materiality' },
                        { title: '默认部门', dataIndex: 'default_owner_department' },
                        { title: '操作', render: (_: unknown, record: Topic) => <Button type="link" onClick={() => openRecommendedMetrics(record)}>推荐指标</Button> },
                      ]} />
                    </Space>
                  </Col>
                  <Col span={8}>
                    <Card title={selectedTopic ? `${selectedTopic.topic_name} 推荐指标` : '推荐指标'}>
                      <Table rowKey="metric_code" size="small" dataSource={recommendedMetrics} pagination={false} columns={[
                        { title: '指标', dataIndex: 'metric_name' },
                        { title: '类型', dataIndex: 'metric_type' },
                        { title: '必填', dataIndex: 'default_required', render: (value: boolean) => value ? <Tag color="red">是</Tag> : <Tag>否</Tag> },
                      ]} />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: 'metrics',
              label: '指标库',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Card>
                    <Form layout="inline" onFinish={handleMetricSearch}>
                      <Form.Item name="keyword" label="关键词"><Input allowClear placeholder="指标编码/名称" /></Form.Item>
                      <Form.Item name="metric_type" label="类型"><Select allowClear style={{ width: 150 }} options={[{ value: 'quantitative', label: '定量' }, { value: 'qualitative', label: '定性' }]} /></Form.Item>
                      <Form.Item name="topic_code" label="议题编码"><Input allowClear placeholder="TOPIC_GHG_EMISSIONS" /></Form.Item>
                      <Button htmlType="submit" type="primary">查询</Button>
                    </Form>
                  </Card>
                  <Table rowKey="metric_code" dataSource={metrics} pagination={{ pageSize: 10 }} columns={[
                    { title: '编码', dataIndex: 'metric_code' },
                    { title: '名称', dataIndex: 'metric_name' },
                    { title: '类型', dataIndex: 'metric_type' },
                    { title: '数据类型', dataIndex: 'data_type' },
                    { title: '默认单位', dataIndex: 'default_unit' },
                    { title: '默认必填', dataIndex: 'default_required', render: (value: boolean) => value ? <Tag color="red">是</Tag> : <Tag>否</Tag> },
                  ]} />
                </Space>
              ),
            },
          ]}
        />
      </Space>
    </main>
  );
}