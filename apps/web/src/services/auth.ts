export interface LoginResponseData {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: { user_id: string; name: string; email: string; status: string };
  available_tenants: Array<{ tenant_id: string; tenant_name: string; roles: string[] }>;
}

export interface CurrentUser {
  user_id: string;
  name: string;
  email: string;
  current_tenant_id: string;
  current_enterprise_id?: string | null;
  roles: string[];
  permissions: string[];
  enterprises: Array<{ enterprise_id: string; enterprise_name: string; enterprise_code?: string; access_scope: string }>;
}

const API_BASE = '/api/v1';

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error?.code ?? 'REQUEST_FAILED');
  }
  return payload.data as T;
}

export async function login(email: string, password: string): Promise<LoginResponseData> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return parseResponse<LoginResponseData>(response);
}

export async function getCurrentUser(token: string): Promise<CurrentUser> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return parseResponse<CurrentUser>(response);
}
