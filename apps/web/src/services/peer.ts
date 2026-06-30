const API_BASE = '/api/v1';

export interface GicsClassification {
  gics_level: number;
  gics_code: string;
  gics_name_en: string;
  gics_name_cn?: string | null;
  confidence?: number | null;
  reason?: string | null;
}

export interface GicsIdentifyResponse {
  enterprise_id: string;
  primary_result: GicsClassification;
  alternative_results: GicsClassification[];
  requires_human_confirmation: boolean;
}

export interface CurrentGicsResponse {
  enterprise_id: string;
  current_gics: (GicsClassification & { confirmed_at?: string; source?: string }) | null;
}

export interface PeerCompany {
  peer_company_id: string;
  profile_peer_company_id?: string;
  company_name: string;
  stock_code?: string | null;
  exchange?: string | null;
  gics_level_4_code?: string | null;
  gics_level_4_name?: string | null;
  business_similarity_score?: number | null;
  industry_leader_score?: number | null;
  report_availability_score?: number | null;
  overall_score?: number | null;
  recommendation_reason?: string | null;
  latest_report_year?: number | null;
  has_report_in_library: boolean;
  selected: boolean;
  confirmed_at?: string | null;
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

export async function identifyGics(token: string, enterpriseId: string, values: { industry_description?: string; main_business?: string } = {}): Promise<GicsIdentifyResponse> {
  return parseResponse<GicsIdentifyResponse>(await fetch(`${API_BASE}/enterprises/${enterpriseId}/gics/identify`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify(values) }));
}

export async function getCurrentGics(token: string, enterpriseId: string): Promise<CurrentGicsResponse> {
  return parseResponse<CurrentGicsResponse>(await fetch(`${API_BASE}/enterprises/${enterpriseId}/gics/current`, { headers: authHeaders(token) }));
}

export async function confirmGics(token: string, enterpriseId: string, gics: GicsClassification): Promise<CurrentGicsResponse> {
  return parseResponse<CurrentGicsResponse>(await fetch(`${API_BASE}/enterprises/${enterpriseId}/gics/confirm`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify({ gics_level: gics.gics_level, gics_code: gics.gics_code, confirmation_note: gics.reason }) }));
}

export async function recommendPeers(token: string, projectId: string): Promise<{ project_id: string; recommended_peers: PeerCompany[] }> {
  return parseResponse<{ project_id: string; recommended_peers: PeerCompany[] }>(await fetch(`${API_BASE}/projects/${projectId}/peer-companies/recommend`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify({ limit: 10, prefer_business_similarity: true, prefer_industry_leaders: true }) }));
}

export async function listProjectPeers(token: string, projectId: string): Promise<{ items: PeerCompany[] }> {
  return parseResponse<{ items: PeerCompany[] }>(await fetch(`${API_BASE}/projects/${projectId}/peer-companies`, { headers: authHeaders(token) }));
}

export async function searchPeerCompanies(token: string, params: { keyword?: string; gics_code?: string } = {}): Promise<{ items: PeerCompany[] }> {
  const search = new URLSearchParams();
  if (params.keyword) search.set('keyword', params.keyword);
  if (params.gics_code) search.set('gics_code', params.gics_code);
  const query = search.toString() ? `?${search.toString()}` : '';
  return parseResponse<{ items: PeerCompany[] }>(await fetch(`${API_BASE}/peer-companies/search${query}`, { headers: authHeaders(token) }));
}

export async function addPeerCompany(token: string, projectId: string, values: { peer_company_id?: string; company_name: string; stock_code?: string; exchange?: string; reason?: string }): Promise<PeerCompany> {
  return parseResponse<PeerCompany>(await fetch(`${API_BASE}/projects/${projectId}/peer-companies`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify(values) }));
}

export async function confirmPeerPool(token: string, projectId: string, selectedPeerCompanyIds: string[]): Promise<{ project_id: string; confirmed_count: number; items: PeerCompany[] }> {
  return parseResponse<{ project_id: string; confirmed_count: number; items: PeerCompany[] }>(await fetch(`${API_BASE}/projects/${projectId}/peer-companies/confirm`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify({ selected_peer_company_ids: selectedPeerCompanyIds }) }));
}

export async function removeProjectPeer(token: string, projectId: string, projectPeerCompanyId: string): Promise<{ removed: boolean }> {
  return parseResponse<{ removed: boolean }>(await fetch(`${API_BASE}/projects/${projectId}/peer-companies/${projectPeerCompanyId}`, { method: 'DELETE', headers: authHeaders(token) }));
}
