const API_BASE = '/api/v1';

export interface FileObject {
  file_id: string;
  file_name: string;
  file_size?: number;
  mime_type?: string;
  upload_status: string;
}

export interface PeerReport {
  peer_report_id: string;
  project_id: string;
  peer_company_id: string;
  file_id: string;
  report_year: number;
  report_name?: string | null;
  report_language?: string | null;
  parse_status: string;
}

export interface AsyncJob {
  job_id: string;
  job_type: string;
  job_status: string;
  progress: number;
  current_step?: string | null;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.success === false) {
    throw new Error(payload.error?.code ?? 'REQUEST_FAILED');
  }
  return payload.data as T;
}

export async function uploadPeerReportFile(token: string, values: { file: File; enterprise_id: string; project_id: string }): Promise<FileObject> {
  const body = new FormData();
  body.append('file', values.file);
  body.append('business_type', 'peer_report');
  body.append('enterprise_id', values.enterprise_id);
  body.append('project_id', values.project_id);
  return parseResponse<FileObject>(await fetch(`${API_BASE}/files/upload`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body }));
}

export async function createPeerReport(token: string, projectId: string, values: { peer_company_id: string; file_id: string; report_year: number; report_name?: string; report_language?: string }): Promise<PeerReport> {
  return parseResponse<PeerReport>(await fetch(`${API_BASE}/projects/${projectId}/peer-reports`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(values) }));
}

export async function listPeerReports(token: string, projectId: string): Promise<{ items: PeerReport[] }> {
  return parseResponse<{ items: PeerReport[] }>(await fetch(`${API_BASE}/projects/${projectId}/peer-reports`, { headers: { Authorization: `Bearer ${token}` } }));
}

export async function startPeerReportParse(token: string, projectId: string, peerReportId: string): Promise<AsyncJob> {
  return parseResponse<AsyncJob>(await fetch(`${API_BASE}/projects/${projectId}/peer-reports/${peerReportId}/parse`, { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ parser_mode: 'mock' }) }));
}
