/** Vacío en dev con proxy de Vite; en prod o llamadas directas: p. ej. http://127.0.0.1:8000 */
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  return localStorage.getItem("almas_token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("almas_token", token);
  else localStorage.removeItem("almas_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = true, headers, ...rest } = options;
  const h = new Headers(headers);
  if (auth) {
    const t = getToken();
    if (t) h.set("Authorization", `Bearer ${t}`);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...rest, headers: h });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const msg =
      typeof data === "object" && data && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(msg, res.status);
  }
  return data as T;
}

export interface BackupConfig {
  enabled: boolean;
  schedule_type: string;
  schedule_time: string;
  schedule_day_of_week: number | null;
  s3_endpoint_url: string | null;
  s3_bucket_name: string;
  s3_region_name: string;
  s3_access_key_id: string;
  has_secret_access_key: boolean;
  s3_prefix: string;
  retention_count: number;
  updated_at: string | null;
}

export interface BackupConfigUpdate {
  enabled: boolean;
  schedule_type: string;
  schedule_time: string;
  schedule_day_of_week: number | null;
  s3_endpoint_url?: string | null;
  s3_bucket_name: string;
  s3_region_name: string;
  s3_access_key_id: string;
  s3_secret_access_key?: string | null;
  s3_prefix: string;
  retention_count: number;
}

export interface BackupLog {
  id: string;
  trigger_type: string;
  status: string;
  file_name: string;
  file_size_bytes: number | null;
  storage_key: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface BackupStatus {
  is_running: boolean;
  last_log: BackupLog | null;
  next_run_at: string | null;
}

export interface BackupRunResponse {
  success: boolean;
  message: string;
  log?: BackupLog | null;
}

export async function getBackupConfig(): Promise<BackupConfig> {
  return apiFetch<BackupConfig>("/api/v1/backups/config");
}

export async function updateBackupConfig(data: BackupConfigUpdate): Promise<BackupConfig> {
  return apiFetch<BackupConfig>("/api/v1/backups/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getBackupStatus(): Promise<BackupStatus> {
  return apiFetch<BackupStatus>("/api/v1/backups/status");
}

export async function runManualBackup(): Promise<BackupRunResponse> {
  return apiFetch<BackupRunResponse>("/api/v1/backups/run", {
    method: "POST",
  });
}

export async function getBackupLogs(limit = 50): Promise<BackupLog[]> {
  return apiFetch<BackupLog[]>(`/api/v1/backups/logs?limit=${limit}`);
}
