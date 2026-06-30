import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  List,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  listClauseMetrics,
  listClauses,
  listMetrics,
  listStandardTopics,
  listStandards,
  listTopicMetrics,
  listTopics,
  getStandard,
} from "../services/standardLibrary";
import type {
  ClauseMetricMap,
  Metric,
  Standard,
  StandardClause,
  StandardTopicMap,
  Topic,
  TopicMetricMap,
} from "../services/standardLibrary";
import { useAuthStore } from "../stores/authStore";

export function StandardLibraryPage() {
  const token = useAuthStore((state) => state.accessToken);
  const [loading, setLoading] = useState(Boolean(token));
import { Alert, Button, Card, Col, Form, Input, Row, Select, Space, Spin, Table, Tabs, Tag, Typography, message } from 'antd';
import type { TablePaginationConfig } from 'antd';
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
  const [selectedStandard, setSelectedStandard] = useState<Standard | null>(
    null,
  );
  const [clauses, setClauses] = useState<StandardClause[]>([]);
  const [standardTopics, setStandardTopics] = useState<StandardTopicMap[]>([]);
  const [topicMetrics, setTopicMetrics] = useState<TopicMetricMap[]>([]);
  const [clauseMetrics, setClauseMetrics] = useState<ClauseMetricMap[]>([]);

  const refresh = async () => {
    if (!token) return;
    setLoading(true);
    const [standardPage, topicPage, metricPage] = await Promise.all([
      listStandards(token, { page_size: "100" }),
      listTopics(token, { page_size: "100" }),
      listMetrics(token, { page_size: "100" }),
    ]);
    setStandards(standardPage.items);
    setTopics(topicPage.items);
    setMetrics(metricPage.items);
    setLoading(false);
  };

  useEffect(() => {
    refresh().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : "REQUEST_FAILED");
      setLoading(false);
    });
  }, [token]);

  const openStandard = async (standardCode: string) => {
    if (!token) return;
    const standard = await getStandard(token, standardCode);
    setSelectedStandard(standard);
    const currentVersion =
      standard.versions?.find((item) => item.is_current) ??
      standard.versions?.[0];
    if (currentVersion) {
      const [clausePage, topicMapPage] = await Promise.all([
        listClauses(
          token,
          standard.standard_code,
          currentVersion.standard_version_code,
        ),
        listStandardTopics(
          token,
          standard.standard_code,
          currentVersion.standard_version_code,
        ),
      ]);
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

  const openClauseMetrics = async (clauseCode: string) => {
    if (!token) return;
    setClauseMetrics((await listClauseMetrics(token, clauseCode)).metrics);
  };

  if (!token) return <Navigate to="/login" replace />;
  if (loading)
    return (
      <main style={{ padding: 24 }}>
        <Spin />
      </main>
    );
  if (error)
    return (
      <main style={{ padding: 24 }}>
        <Alert type="error" message="加载标准库失败" description={error} />
      </main>
    );

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: "100%" }}>
        <Card extra={<Link to="/workbench">返回工作台</Link>}>
          <Typography.Title level={2}>标准库、议题库与指标库</Typography.Title>
          <Typography.Paragraph type="secondary">
            查看公共标准与当前租户私有标准、标准条款、议题指标映射关系。
          </Typography.Paragraph>
  const [standardFilters, setStandardFilters] = useState<{ keyword?: string; standard_type?: string; applicable_market?: string }>({});
  const [standardPagination, setStandardPagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [topicFilters, setTopicFilters] = useState<{ keyword?: string; topic_category?: string }>({});
  const [topicPagination, setTopicPagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [metricFilters, setMetricFilters] = useState<{ keyword?: string; metric_type?: string; topic_code?: string }>({});
  const [metricPagination, setMetricPagination] = useState({ current: 1, pageSize: 50, total: 0 });
  const [recommendedMetrics, setRecommendedMetrics] = useState<Metric[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);

  const refreshAll = async () => {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    try {
      const [standardPage, topicPage, metricPage] = await Promise.all([
        listStandards(accessToken, { page: 1, page_size: standardPagination.pageSize }),
        listTopics(accessToken, { page: 1, page_size: topicPagination.pageSize }),
        listMetrics(accessToken, { page: 1, page_size: metricPagination.pageSize }),
      ]);
      setStandards(standardPage.items);
      setTopics(topicPage.items);
      setMetrics(metricPage.items);
      setStandardPagination((current) => ({ ...current, current: 1, total: standardPage.total }));
      setTopicPagination((current) => ({ ...current, current: 1, total: topicPage.total }));
      setMetricPagination((current) => ({ ...current, current: 1, total: metricPage.total }));
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
    const nextFilters = {
      keyword: values.keyword,
      standard_type: values.standard_type,
      applicable_market: values.applicable_market,
    };
    setStandardFilters(nextFilters);
    await loadStandardPage(nextFilters, 1, standardPagination.pageSize);
    message.success('标准列表已更新');
  };

  const handleTopicSearch = async (values: { keyword?: string; topic_category?: string }) => {
    const nextFilters = {
      keyword: values.keyword,
      topic_category: values.topic_category,
    };
    setTopicFilters(nextFilters);
    await loadTopicPage(nextFilters, 1, topicPagination.pageSize);
    message.success('议题列表已更新');
  };

  const loadStandardPage = async (filters: { keyword?: string; standard_type?: string; applicable_market?: string }, pageNumber: number, pageSize: number) => {
    if (!accessToken) return;
    const page = await listStandards(accessToken, { ...filters, page: pageNumber, page_size: pageSize });
    setStandards(page.items);
    setStandardPagination({ current: pageNumber, pageSize, total: page.total });
  };

  const handleStandardTableChange = (pagination: TablePaginationConfig) => {
    void loadStandardPage(standardFilters, pagination.current ?? 1, pagination.pageSize ?? standardPagination.pageSize);
  };

  const loadTopicPage = async (filters: { keyword?: string; topic_category?: string }, pageNumber: number, pageSize: number) => {
    if (!accessToken) return;
    const page = await listTopics(accessToken, { ...filters, page: pageNumber, page_size: pageSize });
    setTopics(page.items);
    setTopicPagination({ current: pageNumber, pageSize, total: page.total });
  };

  const handleTopicTableChange = (pagination: TablePaginationConfig) => {
    void loadTopicPage(topicFilters, pagination.current ?? 1, pagination.pageSize ?? topicPagination.pageSize);
  };

  const loadMetricPage = async (filters: { keyword?: string; metric_type?: string; topic_code?: string }, pageNumber: number, pageSize: number) => {
    if (!accessToken) return;
    const page = await listMetrics(accessToken, { ...filters, page: pageNumber, page_size: pageSize });
    setMetrics(page.items);
    setMetricPagination({ current: pageNumber, pageSize, total: page.total });
  };

  const handleMetricSearch = async (values: { keyword?: string; metric_type?: string; topic_code?: string }) => {
    const nextFilters = {
      keyword: values.keyword,
      metric_type: values.metric_type,
      topic_code: values.topic_code,
    };
    setMetricFilters(nextFilters);
    await loadMetricPage(nextFilters, 1, metricPagination.pageSize);
    message.success('指标列表已更新');
  };

  const handleMetricTableChange = (pagination: TablePaginationConfig) => {
    void loadMetricPage(metricFilters, pagination.current ?? 1, pagination.pageSize ?? metricPagination.pageSize);
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
              key: "standards",
              label: "标准库列表/详情",
              children: (
                <Row gutter={16}>
                  <Col span={10}>
                    <Card title="标准列表">
                      <Table
                        rowKey="standard_code"
                        size="small"
                        dataSource={standards}
                        pagination={false}
                        columns={[
                          { title: "编码", dataIndex: "standard_code" },
                          { title: "名称", dataIndex: "standard_short_name" },
                          {
                            title: "范围",
                            dataIndex: "scope_type",
                            render: (value) => <Tag>{value}</Tag>,
                          },
                          {
                            title: "操作",
                            render: (_, record) => (
                              <Button
                                type="link"
                                onClick={() =>
                                  openStandard(record.standard_code)
                                }
                              >
                                查看
                              </Button>
                            ),
                          },
                        ]}
                      />
                    </Card>
                  </Col>
                  <Col span={14}>
                    <Card title="标准详情与条款">
                      {selectedStandard ? (
                        <Space direction="vertical" style={{ width: "100%" }}>
                          <Descriptions bordered size="small" column={1}>
                            <Descriptions.Item label="名称">
                              {selectedStandard.standard_name}
                            </Descriptions.Item>
                            <Descriptions.Item label="类型">
                              {selectedStandard.standard_type}
                            </Descriptions.Item>
                            <Descriptions.Item label="发布方">
                              {selectedStandard.issuing_body ?? "-"}
                            </Descriptions.Item>
                            <Descriptions.Item label="说明">
                              {selectedStandard.description ?? "-"}
                            </Descriptions.Item>
                          </Descriptions>
                          <List
                            header="版本"
                            dataSource={selectedStandard.versions ?? []}
                            renderItem={(item) => (
                              <List.Item>
                                {item.version_name}
                                <Tag
                                  color={item.is_current ? "green" : undefined}
                                >
                                  {item.version_no}
                                </Tag>
                              </List.Item>
                            )}
                          />
                          <Table
                            rowKey="clause_code"
                            size="small"
                            dataSource={clauses}
                            pagination={{ pageSize: 5 }}
                            columns={[
                              { title: "条款号", dataIndex: "clause_no" },
                              { title: "标题", dataIndex: "clause_title" },
                              {
                                title: "披露类型",
                                dataIndex: "disclosure_type",
                              },
                              { title: "要求", dataIndex: "is_required" },
                            ]}
                          />
                        </Space>
                      ) : (
                        <Typography.Text type="secondary">
                          请选择标准。
                        </Typography.Text>
                      )}
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: "topics",
              label: "议题库列表",
              children: (
                <Card>
                  <Table
                    rowKey="topic_code"
                    dataSource={topics}
                    columns={[
                      { title: "编码", dataIndex: "topic_code" },
                      { title: "名称", dataIndex: "topic_name" },
                      {
                        title: "类别",
                        dataIndex: "topic_category",
                        render: (value) => <Tag>{value}</Tag>,
                      },
                      { title: "说明", dataIndex: "topic_description" },
                      {
                        title: "指标映射",
                        render: (_, record) => (
                          <Button
                            type="link"
                            onClick={() => openTopicMetrics(record.topic_code)}
                          >
                            查看推荐指标
                          </Button>
                        ),
                      },
                    ]}
                  />
                </Card>
              ),
            },
            {
              key: "metrics",
              label: "指标库列表",
              children: (
                <Card>
                  <Table
                    rowKey="metric_code"
                    dataSource={metrics}
                    columns={[
                      { title: "编码", dataIndex: "metric_code" },
                      { title: "名称", dataIndex: "metric_name" },
                      { title: "类型", dataIndex: "metric_type" },
                      { title: "数据类型", dataIndex: "data_type" },
                      { title: "单位", dataIndex: "default_unit" },
                      {
                        title: "必填",
                        dataIndex: "default_required",
                        render: (value) =>
                          value ? <Tag color="red">是</Tag> : <Tag>否</Tag>,
                      },
                    ]}
                  />
                </Card>
              ),
            },
            {
              key: "maps",
              label: "映射关系查看",
              children: (
                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="标准-议题映射">
                      <Table
                        rowKey="map_id"
                        dataSource={standardTopics}
                        pagination={false}
                        columns={[
                          { title: "议题", dataIndex: "topic_name" },
                          { title: "类别", dataIndex: "topic_category" },
                          {
                            title: "关键议题",
                            dataIndex: "is_key_topic",
                            render: (value) =>
                              value ? (
                                <Tag color="green">是</Tag>
                              ) : (
                                <Tag>否</Tag>
                              ),
                          },
                          {
                            title: "相关条款",
                            dataIndex: "related_clause_codes",
                            render: (value: string[]) => value?.join(", "),
                          },
                        ]}
                      />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Space direction="vertical" style={{ width: "100%" }}>
                      <Card title="议题-指标映射">
                        <Form layout="inline" style={{ marginBottom: 16 }}>
                          <Form.Item label="选择议题">
                            <Select
                              style={{ width: 260 }}
                              options={topics.map((topic) => ({
                                value: topic.topic_code,
                                label: `${topic.topic_code} ${topic.topic_name}`,
                              }))}
                              onChange={openTopicMetrics}
                            />
                          </Form.Item>
                        </Form>
                        <Table
                          rowKey="map_id"
                          dataSource={topicMetrics}
                          pagination={false}
                          columns={[
                            { title: "指标", dataIndex: "metric_name" },
                            { title: "类型", dataIndex: "metric_type" },
                            {
                              title: "必选",
                              dataIndex: "is_required",
                              render: (value) =>
                                value ? (
                                  <Tag color="red">是</Tag>
                                ) : (
                                  <Tag>否</Tag>
                                ),
                            },
                            {
                              title: "默认选中",
                              dataIndex: "default_selected",
                              render: (value) => (value ? "是" : "否"),
                            },
                          ]}
                        />
                      </Card>
                      <Card title="条款-指标映射">
                        <Form layout="inline" style={{ marginBottom: 16 }}>
                          <Form.Item label="选择条款">
                            <Select
                              style={{ width: 260 }}
                              options={clauses.map((clause) => ({
                                value: clause.clause_code,
                                label: `${clause.clause_no} ${clause.clause_title}`,
                              }))}
                              onChange={openClauseMetrics}
                            />
                          </Form.Item>
                        </Form>
                        <Table
                          rowKey="map_id"
                          dataSource={clauseMetrics}
                          pagination={false}
                          columns={[
                            { title: "指标", dataIndex: "metric_name" },
                            {
                              title: "要求类型",
                              dataIndex: "disclosure_requirement_type",
                            },
                            {
                              title: "来源必需",
                              dataIndex: "source_required",
                              render: (value) =>
                                value ? (
                                  <Tag color="red">是</Tag>
                                ) : (
                                  <Tag>否</Tag>
                                ),
                            },
                            {
                              title: "说明",
                              dataIndex: "standard_specific_instruction",
                            },
                          ]}
                        />
                      </Card>
                    </Space>
                  </Col>
                </Row>
              ),
            },
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
                  <Table rowKey="standard_code" dataSource={standards} pagination={{ current: standardPagination.current, pageSize: standardPagination.pageSize, total: standardPagination.total, showSizeChanger: true }} onChange={handleStandardTableChange} columns={[
                    { title: '编码', dataIndex: 'standard_code' },
                    { title: '名称', dataIndex: 'standard_name' },
                    { title: '简称', dataIndex: 'standard_short_name' },
                    { title: '类型', dataIndex: 'standard_type' },
                    { title: '适用市场', dataIndex: 'applicable_market' },
                    { title: '范围', dataIndex: 'scope_type', render: (value: string) => <Tag color={value === 'tenant' ? 'blue' : 'default'}>{value === 'tenant' ? '租户私有' : '平台公共'}</Tag> },
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
                      <Table rowKey="topic_code" dataSource={topics} pagination={{ current: topicPagination.current, pageSize: topicPagination.pageSize, total: topicPagination.total, showSizeChanger: true }} onChange={handleTopicTableChange} columns={[
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
                  <Table rowKey="metric_code" dataSource={metrics} pagination={{ current: metricPagination.current, pageSize: metricPagination.pageSize, total: metricPagination.total, showSizeChanger: true }} onChange={handleMetricTableChange} columns={[
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
