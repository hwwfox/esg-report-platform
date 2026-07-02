import { Alert, Button, Card, Descriptions, Drawer, Form, Input, Space, Table, Tag, Typography } from 'antd';
import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { EsgDataRecord, SourceReference, getEsgDataRecordSources, listEsgDataRecords } from '../services/esgData';
import { useAuthStore } from '../stores/authStore';

export function EsgDataPage() {
  const token = useAuthStore((state) => state.accessToken);
  const [projectId, setProjectId] = useState('');
  const [records, setRecords] = useState<EsgDataRecord[]>([]);
  const [sources, setSources] = useState<SourceReference[]>([]);
  const [activeRecord, setActiveRecord] = useState<EsgDataRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm<Record<string, string>>();

  if (!token) return <Navigate to="/login" replace />;

  const loadRecords = async () => {
    const values = form.getFieldsValue();
    if (!values.project_id) {
      setError('请输入项目ID');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setProjectId(values.project_id);
      const { items } = await listEsgDataRecords(token, values.project_id, {
        topic_code: values.topic_code,
        metric_code: values.metric_code,
        org_unit_id: values.org_unit_id,
        period: values.period,
      });
      setRecords(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'REQUEST_FAILED');
    } finally {
      setLoading(false);
    }
  };

  const openSources = async (record: EsgDataRecord) => {
    setActiveRecord(record);
    setSources([]);
    try {
      const result = await getEsgDataRecordSources(token, projectId, record.data_record_id);
      setSources(result.sources);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'REQUEST_FAILED');
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <Card extra={<Space><Link to="/workbench">工作台</Link><Link to="/recommendations">推荐</Link></Space>}>
        <Typography.Title level={2}>ESG数据表</Typography.Title>
        <Form form={form} layout="inline" onFinish={loadRecords} style={{ marginBottom: 16 }}>
          <Form.Item name="project_id" rules={[{ required: true, message: '请输入项目ID' }]}><Input placeholder="项目ID" style={{ width: 260 }} /></Form.Item>
          <Form.Item name="topic_code"><Input placeholder="议题编码" /></Form.Item>
          <Form.Item name="metric_code"><Input placeholder="指标编码" /></Form.Item>
          <Form.Item name="org_unit_id"><Input placeholder="部门ID" /></Form.Item>
          <Form.Item name="period"><Input placeholder="期间" /></Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>查询</Button>
        </Form>
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
        <Table rowKey="data_record_id" dataSource={records} loading={loading} pagination={{ pageSize: 10 }} columns={[
          { title: '议题', dataIndex: 'topic_name' },
          { title: '指标', dataIndex: 'metric_name' },
          { title: '期间', dataIndex: 'period' },
          { title: '数值', render: (_, row) => row.value ?? row.text_value ?? '-' },
          { title: '单位', dataIndex: 'unit' },
          { title: '部门', dataIndex: 'org_unit_name' },
          { title: '审核', dataIndex: 'review_status', render: (value) => <Tag color="green">{value}</Tag> },
          { title: '报告引用', dataIndex: 'report_reference_status' },
          { title: '操作', render: (_, row) => <Button onClick={() => openSources(row)}>查看来源</Button> },
        ]} />
      </Card>
      <Drawer title="数据来源" open={Boolean(activeRecord)} onClose={() => setActiveRecord(null)} width={560}>
        {activeRecord && <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="数据ID">{activeRecord.data_record_id}</Descriptions.Item>
          <Descriptions.Item label="采集任务">{activeRecord.source_task_id ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="提交记录">{activeRecord.source_submission_id ?? '-'}</Descriptions.Item>
        </Descriptions>}
        <Table rowKey={(row) => `${row.source_type}:${row.source_object_id}`} dataSource={sources} pagination={false} columns={[
          { title: '来源类型', dataIndex: 'source_type' },
          { title: '来源对象', dataIndex: 'source_object_id' },
        ]} />
      </Drawer>
    </main>
  );
}
