const API_BASE = '/api/v1';

export interface Standard {
  standard_code: string;
  standard_name: string;
  standard_short_name?: string | null;
  standard_type: string;
  applicable_market?: string | null;
  current_version?: string | null;
  status: string;
}

export interface Topic {
  topic_code: string;
  topic_name: string;
  topic_category: 'E' | 'S' | 'G';
  default_financial_materiality?: string | null;
  default_impact_materiality?: string | null;
  default_owner_department?: string | null;
  status: string;
}

export interface Metric {
  metric_code: string;
  metric_name: string;
  metric_type: 'quantitative' | 'qualitative';
  data_type: string;
  default_unit?: string | null;
  default_required: boolean;
  status: string;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}

export interface RecommendedMetricsResponse {
  topic_code: string;
  topic_name: string;
  metrics: Metric[];
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error?.code ?? 'REQUEST_FAILED');
  }
  return payload.data as T;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

function queryString(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

export async function listStandards(token: string, params: { keyword?: string; standard_type?: string; applicable_market?: string; page?: number; page_size?: number } = {}): Promise<ListResponse<Standard>> {
  return parseResponse<ListResponse<Standard>>(await fetch(`${API_BASE}/standards${queryString(params)}`, { headers: authHeaders(token) }));
}

export async function listTopics(token: string, params: { keyword?: string; topic_category?: string; page?: number; page_size?: number } = {}): Promise<ListResponse<Topic>> {
  return parseResponse<ListResponse<Topic>>(await fetch(`${API_BASE}/topics${queryString(params)}`, { headers: authHeaders(token) }));
}

export async function listMetrics(token: string, params: { keyword?: string; metric_type?: string; topic_code?: string; page?: number; page_size?: number } = {}): Promise<ListResponse<Metric>> {
  return parseResponse<ListResponse<Metric>>(await fetch(`${API_BASE}/metrics${queryString(params)}`, { headers: authHeaders(token) }));
}

export async function getRecommendedMetrics(token: string, topicCode: string): Promise<RecommendedMetricsResponse> {
  return parseResponse<RecommendedMetricsResponse>(await fetch(`${API_BASE}/topics/${encodeURIComponent(topicCode)}/recommended-metrics`, { headers: authHeaders(token) }));
}
