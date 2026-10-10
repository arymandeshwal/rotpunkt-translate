import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

// Types generated from the backend's OpenAPI schema (`npm run gen:api`).
type Schemas = components["schemas"];
export type HealthResponse = Schemas["HealthResponse"];
export type LanguageCode = Schemas["TermIn"]["language"];
export type Language = Schemas["LanguageOut"];
export type GlossaryCategory = Schemas["GlossaryEntryOut"]["category"];
export type GlossaryEntry = Schemas["GlossaryEntryOut"];
export type GlossaryEntryCreate = Schemas["GlossaryEntryCreate"];
export type GlossaryEntryUpdate = Schemas["GlossaryEntryUpdate"];
export type GlossaryPage = Schemas["GlossaryPage"];

export const api = createClient<paths>({
  // Requests must be absolute; the dev server proxies /api to the backend.
  baseUrl: globalThis.location.origin,
  // Resolve fetch per call (not at import time) so tests can stub it.
  fetch: (request) => {
    // Intercept and inject Authorization token if present
    const token = localStorage.getItem("auth_token");
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return globalThis.fetch(request);
  },
});

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    super(`Request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

/** Return the response data, or throw an ApiError carrying the error body. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data === undefined) {
    throw new ApiError(result.response.status, result.error);
  }
  return result.data;
}

// The health endpoint answers 503 with a body describing what is degraded.
export async function getHealth(): Promise<HealthResponse> {
  const { data, error, response } = await api.GET("/api/health");
  if (data) return data;
  if (response.status === 503 && error) return error;
  throw new ApiError(response.status, error);
}
