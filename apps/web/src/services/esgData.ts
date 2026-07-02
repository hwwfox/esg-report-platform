const API_BASE = '/api/v1';

export interface EsgDataRecord {
  data_record_id: string;
  project_id: string;
  topic_code?: string | null;
  topic_name?: string | null;
  metric_code?: string | null;
  metric_name?: string | null;
  data_type?: string | null;
  value?: string | number | null;
  text_value?: string | null;
  unit?: string | null;
  period?: string | null;
  org_unit_id?: string | null;
  org_unit_name?: string | null;
  source_task_id?: string | null;
  source_submission_id?: string | null;
  source_file_ids?: string[];
  review_status: string;
  report_reference_status: string;
}

export interface SourceReference {
  source_type: string;
  source_object_id?: string | null;
  target_object_type: string;
  target_object_id: string;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error?.code ?? 'REQUEST_FAILED');
  }
  return payload.data as T;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

export async function listEsgDataRecords(token: string, projectId: string, filters: Record<string, string> = {}): Promise<{ items: EsgDataRecord[]; total: number }> {
  const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
  const query = params.toString() ? `?${params.toString()}` : '';
  return parseResponse<{ items: EsgDataRecord[]; total: number }>(await fetch(`${API_BASE}/projects/${projectId}/esg-data-records${query}`, { headers: authHeaders(token) }));
}

export async function getEsgDataRecordSources(token: string, projectId: string, dataRecordId: string): Promise<{ sources: SourceReference[] }> {
  return parseResponse<{ sources: SourceReference[] }>(await fetch(`${API_BASE}/projects/${projectId}/esg-data-records/${dataRecordId}/sources`, { headers: authHeaders(token) }));
}
