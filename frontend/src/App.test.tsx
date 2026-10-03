import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppRoutes } from "./App";
import { baseRoutes, page } from "./test/glossaryFixtures";
import { mockApi } from "./test/mockApi";
import { mockFetchJson, renderWithProviders } from "./test/render";

describe("App shell", () => {
  it("renders the projects page at /", () => {
    mockFetchJson({ status: "ok", database: "ok" });
    renderWithProviders(<AppRoutes />);

    expect(screen.getByRole("heading", { name: "Projects" })).toBeInTheDocument();
  });

  it("navigates to the glossary page", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([]) } });
    renderWithProviders(<AppRoutes />);

    await userEvent.click(screen.getByRole("link", { name: "Glossary" }));

    expect(screen.getByRole("heading", { name: "Glossary" })).toBeInTheDocument();
    expect(await screen.findByText("The glossary is empty")).toBeInTheDocument();
  });
});

describe("HealthBadge", () => {
  it("shows online when the API and database are healthy", async () => {
    mockFetchJson({ status: "ok", database: "ok" });
    renderWithProviders(<AppRoutes />);

    expect(await screen.findByText("All systems online")).toBeInTheDocument();
  });

  it("shows database unavailable on a degraded response", async () => {
    mockFetchJson({ status: "degraded", database: "unavailable" }, 503);
    renderWithProviders(<AppRoutes />);

    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  });

  it("shows offline when the API cannot be reached", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    renderWithProviders(<AppRoutes />);

    expect(await screen.findByText("API offline")).toBeInTheDocument();
  });
});
