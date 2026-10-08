import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { ProjectsPage } from "../ProjectsPage";
import { ProjectSetupPage } from "../ProjectSetupPage";
import type { components } from "../../api/schema";

type ProjectResponse = components["schemas"]["ProjectResponse"];

// Mock the openapi-fetch client
vi.mock("../../api/client", () => ({
  api: {
    POST: vi.fn(),
    GET: vi.fn(),
    PATCH: vi.fn(),
  },
}));

import { api } from "../../api/client";

function renderWithProviders(ui: React.ReactElement, initialRoute = "/") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/" element={ui} />
          <Route path="/projects/:id/setup" element={<ProjectSetupPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function createMockProject(overrides: Partial<ProjectResponse> = {}): ProjectResponse {
  return {
    id: "123",
    name: "test",
    status: "new",
    created_at: "2026-10-05T00:00:00Z",
    updated_at: "2026-10-05T00:00:00Z",
    documents: [{ 
      id: "doc-123",
      original_filename: "test.pdf",
      source_language: "de",
      pages: [{
        id: "page-123",
        number: 1,
        width: 595,
        height: 842,
        warnings: []
      }],
      segments: []
    }],
    ...overrides
  };
}

describe("Projects Upload Flow", () => {
  it("renders the dropzone and uploads a file", async () => {
    // Mock the POST response
    vi.mocked(api.POST).mockResolvedValueOnce({
      data: createMockProject(),
      error: undefined,
      response: new Response()
    });

    // Mock the GET response for the setup page
    vi.mocked(api.GET).mockResolvedValueOnce({
      data: createMockProject({
        documents: [{ 
          id: "doc-123",
          original_filename: "test.pdf",
          source_language: "de",
          pages: [{
            id: "page-123",
            number: 1,
            width: 595,
            height: 842,
            warnings: []
          }], 
          segments: [
            {
              id: "seg-1",
              page_number: 1,
              order_index: 0,
              kind: "heading",
              text: "Hello",
              bounding_box: [0,0,10,10],
              detected_language: "en",
              is_translatable: false,
              translations: {}
            }
          ] 
        }]
      }),
      error: undefined,
      response: new Response()
    });

    renderWithProviders(<ProjectsPage />);
    
    expect(screen.getByText("Drag & drop your PDF here")).toBeInTheDocument();
    
    // Create a dummy PDF file
    const file = new File(["dummy pdf content"], "test.pdf", { type: "application/pdf" });
    const input = document.getElementById("file-upload") as HTMLInputElement;
    
    // Trigger upload
    await userEvent.upload(input, file);
    
    // Verify POST was called
    expect(api.POST).toHaveBeenCalledWith("/api/projects", expect.any(Object));
    
    // Verify we navigated to the setup page (it should render the file name)
    await waitFor(() => {
      expect(screen.getByText("test.pdf")).toBeInTheDocument();
    });
    expect(screen.getByText("Project Setup")).toBeInTheDocument();
  });
});
