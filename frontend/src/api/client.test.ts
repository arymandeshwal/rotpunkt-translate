import { describe, expect, it } from "vitest";

import { mockFetchJson } from "@/test/render";

import { ApiError, api, unwrap } from "./client";

describe("api client", () => {
  it("sends requests to the same-origin /api path", async () => {
    const fetchMock = mockFetchJson([{ code: "de", name: "German" }]);

    const languages = unwrap(await api.GET("/api/languages"));

    expect(languages).toEqual([{ code: "de", name: "German" }]);
    const request = fetchMock.mock.calls[0]![0] as Request;
    expect(new URL(request.url).pathname).toBe("/api/languages");
  });

  it("unwrap throws an ApiError carrying status and body", async () => {
    mockFetchJson({ detail: "Glossary entry 7 not found" }, 404);

    const result = await api.GET("/api/glossary/{entry_id}", {
      params: { path: { entry_id: 7 } },
    });

    expect(() => unwrap(result)).toThrow(ApiError);
    try {
      unwrap(result);
    } catch (error) {
      expect((error as ApiError).status).toBe(404);
      expect((error as ApiError).body).toEqual({ detail: "Glossary entry 7 not found" });
    }
  });
});
