const API_BASE = '/api/v1';

export interface Paged<T> { items: T[]; page: number; page_size: number; total: number }
export interface Standard { standard_id: string; standard_code: string; standard_name: string; standard_short_name?: string | null; standard_type: string; applicable_market?: string | null; issuing_body?: string | null; description?: string | null; scope_type: string; status: string; versions?: StandardVersion[] }
export interface StandardVersion { standard_version_id: string; standard_version_code: string; version_name: string; version_no: string; effective_date?: string | null; is_current: boolean; status: string }
export interface StandardClause { clause_id: string; clause_code: string; clause_no: string; clause_title: string; clause_level: number; clause_text: string; disclosure_type: string; is_required: string; status: string }
export interface Topic { topic_id: string; topic_code: string; topic_name: string; topic_category: string; topic_description?: string | null; status: string }
export interface Metric { metric_id: string; metric_code: string; metric_name: string; metric_type: string; data_type: string; default_unit?: string | null; default_required: boolean; status: string }
export interface TopicMetricMap extends Metric { map_id: string; default_selected: boolean; is_required: boolean; sort_order: number }
export interface StandardTopicMap { map_id: string; topic_code: string; topic_name: string; topic_category: string; related_clause_codes: string[]; is_key_topic: boolean; status: string }

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok || payload.success === false) throw new Error(payload.error?.code ?? 'REQUEST_FAILED');
  return payload.data as T;
}

function authHeaders(token: string) { return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }; }
function query(params: Record<string, string | undefined>) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => { if (value) q.set(key, value); });
  return q.toString() ? `?${q.toString()}` : '';
}

export async function listStandards(token: string, params: Record<string, string | undefined> = {}) { return parseResponse<Paged<Standard>>(await fetch(`${API_BASE}/standards${query(params)}`, { headers: authHeaders(token) })); }
export async function getStandard(token: string, standardCode: string) { return parseResponse<Standard>(await fetch(`${API_BASE}/standards/${encodeURIComponent(standardCode)}`, { headers: authHeaders(token) })); }
export async function listClauses(token: string, standardCode: string, versionCode: string) { return parseResponse<Paged<StandardClause>>(await fetch(`${API_BASE}/standards/${encodeURIComponent(standardCode)}/versions/${encodeURIComponent(versionCode)}/clauses?page_size=200`, { headers: authHeaders(token) })); }
export async function listTopics(token: string, params: Record<string, string | undefined> = {}) { return parseResponse<Paged<Topic>>(await fetch(`${API_BASE}/topics${query(params)}`, { headers: authHeaders(token) })); }
export async function listMetrics(token: string, params: Record<string, string | undefined> = {}) { return parseResponse<Paged<Metric>>(await fetch(`${API_BASE}/metrics${query(params)}`, { headers: authHeaders(token) })); }
export async function listStandardTopics(token: string, standardCode: string, versionCode: string) { return parseResponse<{ items: StandardTopicMap[] }>(await fetch(`${API_BASE}/standards/${encodeURIComponent(standardCode)}/versions/${encodeURIComponent(versionCode)}/topics`, { headers: authHeaders(token) })); }
export async function listTopicMetrics(token: string, topicCode: string) { return parseResponse<{ topic_code: string; metrics: TopicMetricMap[] }>(await fetch(`${API_BASE}/topics/${encodeURIComponent(topicCode)}/recommended-metrics`, { headers: authHeaders(token) })); }
