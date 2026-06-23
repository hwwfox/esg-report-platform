import type { CurrentUser } from './auth';

const API_BASE = '/api/v1';

export interface Enterprise {
  enterprise_id: string;
  tenant_id: string;
  enterprise_code?: string | null;
  enterprise_name: string;
  enterprise_short_name?: string | null;
  stock_code?: string | null;
  exchange?: string | null;
  country_or_region?: string | null;
  industry_description?: string | null;
  main_business?: string | null;
  status: string;
}

export interface Project {
  project_id: string;
  enterprise_id: string;
  project_name: string;
  report_year: number;
  report_type: string;
  report_language: string;
  project_owner_user_id: string;
  project_status: string;
  created_at?: string;
  updated_at?: string;
}

export interface ProjectMember {
  project_member_id: string;
  project_id: string;
  user_id: string;
  name: string;
  email: string;
  project_role: string;
  status: string;
}

export interface Paged<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error?.code ?? 'REQUEST_FAILED');
  }
  return payload.data as T;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

export async function listEnterprises(token: string): Promise<Paged<Enterprise>> {
  return parseResponse<Paged<Enterprise>>(await fetch(`${API_BASE}/enterprises`, { headers: authHeaders(token) }));
}

export async function createEnterprise(token: string, values: Pick<Enterprise, 'enterprise_name' | 'enterprise_short_name' | 'stock_code' | 'exchange' | 'country_or_region' | 'industry_description' | 'main_business'>): Promise<Enterprise> {
  return parseResponse<Enterprise>(await fetch(`${API_BASE}/enterprises`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify(values) }));
}

export async function listProjects(token: string, enterpriseId?: string): Promise<Paged<Project>> {
  const query = enterpriseId ? `?enterprise_id=${encodeURIComponent(enterpriseId)}` : '';
  return parseResponse<Paged<Project>>(await fetch(`${API_BASE}/projects${query}`, { headers: authHeaders(token) }));
}

export async function createProject(token: string, values: { enterprise_id: string; project_name: string; report_year: number; project_owner_user_id: string; report_type: string; report_language: string }): Promise<Project> {
  return parseResponse<Project>(await fetch(`${API_BASE}/projects`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify(values) }));
}

export async function getProjectDashboard(token: string, projectId: string): Promise<{ project: Project; progress: Record<string, number>; risks: unknown[]; next_steps: unknown[] }> {
  return parseResponse<{ project: Project; progress: Record<string, number>; risks: unknown[]; next_steps: unknown[] }>(await fetch(`${API_BASE}/projects/${projectId}/dashboard`, { headers: authHeaders(token) }));
}

export async function listProjectMembers(token: string, projectId: string): Promise<{ items: ProjectMember[] }> {
  return parseResponse<{ items: ProjectMember[] }>(await fetch(`${API_BASE}/projects/${projectId}/members`, { headers: authHeaders(token) }));
}

export async function addProjectMember(token: string, projectId: string, user: CurrentUser): Promise<{ items: ProjectMember[] }> {
  return parseResponse<{ items: ProjectMember[] }>(await fetch(`${API_BASE}/projects/${projectId}/members`, { method: 'POST', headers: authHeaders(token), body: JSON.stringify({ user_id: user.user_id, project_role: 'member' }) }));
}
