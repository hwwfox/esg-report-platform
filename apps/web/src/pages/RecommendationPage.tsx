import { Alert, Button, Card, Form, Input, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import type { Recommendation } from '../services/recommendations';
import { acceptProjectTopics, confirmProjectStandards, generateStandardRecommendations, generateTopicRecommendations, listStandardRecommendations, listTopicRecommendations } from '../services/recommendations';
import { useAuthStore } from '../stores/authStore';

const levelColor: Record<string, string> = { high: 'green', medium: 'blue', low: 'orange' };

export function RecommendationPage() {
  const token = useAuthStore((state) => state.accessToken);
  const [projectId, setProjectId] = useState('');
  const [standards, setStandards] = useState<Recommendation[]>([]);
  const [topics, setTopics] = useState<Recommendation[]>([]);
  const [selectedStandardIds, setSelectedStandardIds] = useState<string[]>([]);
  const [selectedTopicIds, setSelectedTopicIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const canLoad = Boolean(token && projectId.trim());

  const load = async () => {
    if (!token || !projectId.trim()) return;
    setLoading(true);
    try {
      const [standardResponse, topicResponse] = await Promise.all([
        listStandardRecommendations(token, projectId.trim()),
        listTopicRecommendations(token, projectId.trim()),
      ]);
      setStandards(standardResponse.items);
      setTopics(topicResponse.items);
      setSelectedStandardIds(standardResponse.items.filter((item) => item.selected).map((item) => item.recommendation_id));
      setSelectedTopicIds(topicResponse.items.filter((item) => item.selected).map((item) => item.recommendation_id));
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载推荐失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const columns = useMemo(() => [
    { title: '编码', render: (_: unknown, record: Recommendation) => record.standard_code ?? record.topic_code },
    { title: '名称', dataIndex: 'item_name' },
    { title: '采用率', render: (_: unknown, record: Recommendation) => `${Math.round((record.adoption_rate ?? 0) * 100)}%` },
    { title: '采用/样本', render: (_: unknown, record: Recommendation) => `${record.adopted_company_count}/${record.analyzed_report_count}` },
    { title: '等级', dataIndex: 'recommendation_level', render: (value: string) => <Tag color={levelColor[value] ?? 'default'}>{value}</Tag> },
    { title: '来源数', dataIndex: 'source_count' },
    { title: '推荐理由', dataIndex: 'reason' },
  ], []);

  const handleGenerate = async () => {
    if (!token || !projectId.trim()) return;
    setLoading(true);
    try {
      await generateStandardRecommendations(token, projectId.trim());
      await generateTopicRecommendations(token, projectId.trim());
      message.success('推荐已生成');
      await load();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '生成推荐失败');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmStandards = async () => {
    if (!token || !projectId.trim()) return;
    const selectedCodes = standards.filter((item) => selectedStandardIds.includes(item.recommendation_id)).map((item) => item.standard_code).filter(Boolean) as string[];
    await confirmProjectStandards(token, projectId.trim(), selectedCodes);
    message.success('项目标准已确认');
    await load();
  };

  const handleAcceptTopics = async () => {
    if (!token || !projectId.trim()) return;
    await acceptProjectTopics(token, projectId.trim(), selectedTopicIds);
    message.success('推荐议题已形成项目快照');
    await load();
  };

  return (
    <main style={{ padding: 24 }}>
      <Typography.Title level={2}>推荐标准与议题</Typography.Title>
      <Alert style={{ marginBottom: 16 }} type="info" showIcon message="采用率、采用企业数和样本数均由系统基于已人工审核的同行报告统计；AI仅可辅助生成理由与限制说明。" />
      <Card style={{ marginBottom: 16 }}>
        <Form layout="inline" onFinish={load}>
          <Form.Item label="项目ID" required>
            <Input style={{ width: 360 }} value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder="输入 report_projects.project_id" />
          </Form.Item>
          <Space>
            <Button htmlType="submit" disabled={!canLoad} loading={loading}>加载</Button>
            <Button type="primary" disabled={!canLoad} loading={loading} onClick={handleGenerate}>生成推荐</Button>
          </Space>
        </Form>
      </Card>
      <Card title="推荐标准" extra={<Button disabled={!selectedStandardIds.length} onClick={handleConfirmStandards}>确认项目标准</Button>} style={{ marginBottom: 16 }}>
        <Table rowKey="recommendation_id" loading={loading} dataSource={standards} columns={columns} rowSelection={{ selectedRowKeys: selectedStandardIds, onChange: (keys) => setSelectedStandardIds(keys as string[])  }} pagination={false} />
      </Card>
      <Card title="推荐议题" extra={<Button disabled={!selectedTopicIds.length} onClick={handleAcceptTopics}>接受议题并生成指标快照</Button>}>
        <Table rowKey="recommendation_id" loading={loading} dataSource={topics} columns={columns} rowSelection={{ selectedRowKeys: selectedTopicIds, onChange: (keys) => setSelectedTopicIds(keys as string[]) }} pagination={false} />
      </Card>
    </main>
  );
}
