const API_BASE = '/api/v1';

export interface SourceReference {
  peer_report_id?: string;
  source_type?: string;
  item_code?: string;
  page_no?: number;
  section_title?: string;
  quoted_text?: string;
  [key: string]: unknown;
}

export interface Recommendation {
  recommendation_id: string;
  item_type: 'standard' | 'topic';
  standard_code?: string | null;
  topic_code?: string | null;
  item_name: string;
  adoption_rate: number;
  adopted_company_count: number;
  analyzed_report_count: number;
  recommendation_level: string;
  reason?: string | null;
  limitations?: string[];
  source_count: number;
  selected: boolean;
  financial_materiality_distribution?: Record<string, number>;
  impact_materiality_distribution?: Record<string, number>;
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

export async function generateStandardRecommendations(token: string, projectId: string) {
  return parseResponse(await fetch(`${API_BASE}/projects/${projectId}/recommendations/standards/generate`, {
    method: 'POST', headers: authHeaders(token), body: JSON.stringify({ based_on_peer_reports: true, only_approved_peer_reports: true, include_ai_reason: true }),
  }));
}

export async function generateTopicRecommendations(token: string, projectId: string) {
  return parseResponse(await fetch(`${API_BASE}/projects/${projectId}/recommendations/topics/generate`, {
    method: 'POST', headers: authHeaders(token), body: JSON.stringify({ based_on_peer_reports: true, only_approved_peer_reports: true, include_materiality_distribution: true, include_ai_reason: true }),
  }));
}

export async function listStandardRecommendations(token: string, projectId: string): Promise<{ items: Recommendation[] }> {
  return parseResponse<{ items: Recommendation[] }>(await fetch(`${API_BASE}/projects/${projectId}/recommendations/standards`, { headers: authHeaders(token) }));
}

export async function listTopicRecommendations(token: string, projectId: string): Promise<{ items: Recommendation[] }> {
  return parseResponse<{ items: Recommendation[] }>(await fetch(`${API_BASE}/projects/${projectId}/recommendations/topics`, { headers: authHeaders(token) }));
}

export async function getRecommendationSources(token: string, projectId: string, recommendationId: string): Promise<{ recommendation_id: string; sources: SourceReference[] }> {
  return parseResponse<{ recommendation_id: string; sources: SourceReference[] }>(await fetch(`${API_BASE}/projects/${projectId}/recommendations/${recommendationId}/sources`, { headers: authHeaders(token) }));
}

export async function confirmProjectStandards(token: string, projectId: string, selectedStandardCodes: string[]) {
  return parseResponse(await fetch(`${API_BASE}/projects/${projectId}/standards/confirm`, {
    method: 'POST', headers: authHeaders(token), body: JSON.stringify({ selected_standard_codes: selectedStandardCodes }),
  }));
}

export async function acceptProjectTopics(token: string, projectId: string, recommendationIds: string[]) {
  return parseResponse(await fetch(`${API_BASE}/projects/${projectId}/topics/accept`, {
    method: 'POST', headers: authHeaders(token), body: JSON.stringify({ recommendation_ids: recommendationIds }),
  }));
}
