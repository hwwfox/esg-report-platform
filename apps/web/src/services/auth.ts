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

export interface RefreshTokenResponseData {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

interface ErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
  success?: boolean;
}

export class AuthApiError extends Error {
  constructor(
    public readonly code: string,
    message?: string,
  ) {
    super(message ?? code);
    this.name = 'AuthApiError';
  }
}

const API_BASE = '/api/v1';

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as ErrorPayload & { data?: T };
  if (!response.ok || payload.success === false) {
    const code = payload.error?.code ?? 'REQUEST_FAILED';
    throw new AuthApiError(code, payload.error?.message ?? code);
  }
  if (payload.data === undefined) {
    throw new AuthApiError('RESPONSE_DATA_MISSING', 'Response data is missing');
  }
  return payload.data;
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

export async function refreshToken(refreshTokenValue: string): Promise<RefreshTokenResponseData> {
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshTokenValue }),
  });
  return parseResponse<RefreshTokenResponseData>(response);
}

export async function logoutRequest(token: string): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  await parseResponse<{ logged_out: boolean }>(response);
}
