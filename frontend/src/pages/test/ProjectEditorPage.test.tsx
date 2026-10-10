import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { ProjectEditorPage } from "../../pages/ProjectEditorPage";
import { useProject, useRetranslateSegment, useEditSegment } from "../../hooks/useProjects";
import { vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../../hooks/useProjects");

describe("ProjectEditorPage", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  const renderWithClient = (ui: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    );
  };

  it("renders loading state", () => {
    vi.mocked(useProject).mockReturnValue({ isLoading: true } as any);
    const { container } = renderWithClient(
      <MemoryRouter initialEntries={["/projects/test-id"]}>
        <Routes>
          <Route path="/projects/:id" element={<ProjectEditorPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders translating state", () => {
    vi.mocked(useProject).mockReturnValue({
      isLoading: false,
      data: {
        id: "test-id",
        name: "Test Project",
        status: "translating",
        documents: [{ id: "doc-1", segments: [] }],
      }
    } as any);

    renderWithClient(
      <MemoryRouter initialEntries={["/projects/test-id"]}>
        <Routes>
          <Route path="/projects/:id" element={<ProjectEditorPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Translating document...")).toBeInTheDocument();
  });

  it("renders segments", () => {
    vi.mocked(useRetranslateSegment).mockReturnValue({ isPending: false, mutate: vi.fn() } as any);
    vi.mocked(useEditSegment).mockReturnValue({ isPending: false, mutate: vi.fn() } as any);
    vi.mocked(useProject).mockReturnValue({
      isLoading: false,
      data: {
        id: "test-id",
        name: "Test Project",
        status: "review",
        documents: [
          {
            id: "doc-1",
            original_filename: "test.pdf",
            source_language: "de",
            segments: [
              {
                id: "seg-1",
                text: "Korpus",
                is_translatable: true,
                translations: { en: "Cabinet body" },
                annotations: { en: [] }
              }
            ]
          }
        ],
      }
    } as any);

    renderWithClient(
      <MemoryRouter initialEntries={["/projects/test-id"]}>
        <Routes>
          <Route path="/projects/:id" element={<ProjectEditorPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Korpus")).toBeInTheDocument();
    expect(screen.getByText("Cabinet body")).toBeInTheDocument();
  });
});
