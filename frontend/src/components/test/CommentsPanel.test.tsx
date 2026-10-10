import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CommentsPanel } from "../CommentsPanel";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { SegmentCommentResponse } from "../../api/client";

vi.mock("../../hooks/useProjects", () => ({
  useAddSegmentComment: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteSegmentComment: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("CommentsPanel", () => {
  const queryClient = new QueryClient();

  const renderWithProviders = (ui: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    );
  };

  it("renders empty state", () => {
    renderWithProviders(<CommentsPanel projectId="p1" segmentId="s1" comments={[]} />);
    expect(screen.getByText(/No comments yet/)).toBeInTheDocument();
  });

  it("renders comments", () => {
    const comments = [
      { id: "c1", segment_id: "s1", user_id: "2", text: "First comment", created_at: new Date().toISOString(), updated_at: new Date().toISOString(), user: { id: "2", email: "other@test.com" } }
    ] as SegmentCommentResponse[];
    
    renderWithProviders(<CommentsPanel projectId="p1" segmentId="s1" comments={comments} />);
    expect(screen.getByText("First comment")).toBeInTheDocument();
    expect(screen.getByText("other@test.com")).toBeInTheDocument();
  });

  it("disables send button when empty", () => {
    renderWithProviders(<CommentsPanel projectId="p1" segmentId="s1" comments={[]} />);
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });
});
