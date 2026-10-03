export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`);
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
}

// The health endpoint answers 503 with a body describing what is degraded.
export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (response.ok || response.status === 503) {
    return (await response.json()) as HealthResponse;
  }
  throw new ApiError(response.status, `GET /health failed with ${response.status}`);
}
