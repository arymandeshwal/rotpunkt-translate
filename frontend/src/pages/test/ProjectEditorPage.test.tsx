import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { ProjectEditorPage } from "../../pages/ProjectEditorPage";
import { useProject, useRetranslateSegment } from "../../hooks/useProjects";
import { vi } from "vitest";

vi.mock("../../hooks/useProjects");

describe("ProjectEditorPage", () => {
  it("renders loading state", () => {
    vi.mocked(useProject).mockReturnValue({ isLoading: true } as any);
    const { container } = render(
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

    render(
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

    render(
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
