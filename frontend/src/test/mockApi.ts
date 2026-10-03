import { vi } from "vitest";

export interface RecordedRequest {
  method: string;
  path: string;
  query: URLSearchParams;
  body: unknown;
}

type Reply = { status?: number; body?: unknown };
type Handler = (request: RecordedRequest & { params: Record<string, string> }) => Reply;

/**
 * Stub fetch with handlers keyed like "GET /api/glossary" or "PATCH /api/glossary/:id".
 * Returns every request the app made, for assertions. Unmatched requests answer 404.
 */
export function mockApi(routes: Record<string, Handler | Reply>) {
  const requests: RecordedRequest[] = [];
  const compiled = Object.entries(routes).map(([key, handler]) => {
    const [method, pattern] = key.split(" ") as [string, string];
    const names: string[] = [];
    const regex = new RegExp(
      "^" + pattern.replace(/:(\w+)/g, (_, name: string) => (names.push(name), "([^/]+)")) + "$",
    );
    return { method, regex, names, handler };
  });

  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const request = input instanceof Request ? input : new Request(input);
    const url = new URL(request.url);
    const text = await request.text();
    const recorded: RecordedRequest = {
      method: request.method,
      path: url.pathname,
      query: url.searchParams,
      body: text ? JSON.parse(text) : undefined,
    };
    requests.push(recorded);

    for (const route of compiled) {
      const match = route.method === request.method && route.regex.exec(url.pathname);
      if (!match) continue;
      const params = Object.fromEntries(route.names.map((name, i) => [name, match[i + 1]!]));
      const reply =
        typeof route.handler === "function" ? route.handler({ ...recorded, params }) : route.handler;
      const status = reply.status ?? 200;
      const body = reply.body === undefined || status === 204 ? null : JSON.stringify(reply.body);
      return new Response(body, { status, headers: { "Content-Type": "application/json" } });
    }
    return new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 });
  });

  return {
    requests,
    /** Requests to a path, optionally filtered by method. */
    to(path: string, method = "GET") {
      return requests.filter((r) => r.path === path && r.method === method);
    },
  };
}
