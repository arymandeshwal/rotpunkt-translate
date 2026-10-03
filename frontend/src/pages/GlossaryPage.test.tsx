import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AppRoutes } from "@/App";
import { HOCHSCHRANK, LANGUAGES, ZEROX, baseRoutes, page } from "@/test/glossaryFixtures";
import { mockApi } from "@/test/mockApi";
import { renderWithProviders } from "@/test/render";

function renderGlossary(route = "/glossary") {
  return renderWithProviders(<AppRoutes />, { route });
}

function lastListQuery(api: ReturnType<typeof mockApi>) {
  return api.to("/api/glossary").at(-1)!.query;
}

describe("Glossary table", () => {
  it("shows every language column by default, plus category and description", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();

    await screen.findByText("Hochschrank");
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual([...LANGUAGES.map((l) => l.name), "Category", "Description"]);
  });

  it("renders terms, missing translations, category and description", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();

    const row = (await screen.findByText("Hochschrank")).closest("tr")!;
    expect(within(row).getByText("tall unit")).toBeInTheDocument();
    expect(within(row).getAllByText("missing")).toHaveLength(5);
    expect(within(row).getByText("Kitchen term")).toBeInTheDocument();
    expect(within(row).getByText("Floor-standing cabinet at full room height")).toBeInTheDocument();
  });

  it("shows a protected entry's term in every language with a lock", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([ZEROX]) } });
    renderGlossary();

    const row = (await screen.findAllByText("Zerox HPL XT"))[0]!.closest("tr")!;
    expect(within(row).getAllByText("Zerox HPL XT")).toHaveLength(LANGUAGES.length);
    expect(within(row).getAllByLabelText("Do not translate")).toHaveLength(LANGUAGES.length);
    expect(within(row).queryByText("missing")).not.toBeInTheDocument();
  });

  it("shows the entry count", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK, ZEROX]) } });
    renderGlossary();

    expect(await screen.findByText(/2 entries\./)).toBeInTheDocument();
  });

  it("searches after the user stops typing", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.type(screen.getByLabelText("Search terms in all languages"), "hoch");

    await waitFor(() => expect(lastListQuery(api).get("q")).toBe("hoch"));
    // One request for the initial load and one for the finished search, not one per keystroke.
    expect(api.to("/api/glossary")).toHaveLength(2);
  });

  it("filters by category", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("combobox", { name: "Category" }));
    await userEvent.click(await screen.findByRole("option", { name: "Product name" }));

    await waitFor(() => expect(lastListQuery(api).get("category")).toBe("product_name"));
  });

  it("filters by missing language", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("combobox", { name: "Missing translation in" }));
    await userEvent.click(await screen.findByRole("option", { name: "French" }));

    await waitFor(() => expect(lastListQuery(api).get("missing")).toBe("fr"));
  });

  it("filters do-not-translate entries", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([ZEROX]) } });
    renderGlossary();
    await screen.findAllByText("Zerox HPL XT");

    await userEvent.click(screen.getByRole("checkbox", { name: "Do not translate" }));

    await waitFor(() => expect(lastListQuery(api).get("do_not_translate")).toBe("true"));
  });

  it("filters case-sensitive entries", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([ZEROX]) } });
    renderGlossary();
    await screen.findAllByText("Zerox HPL XT");

    await userEvent.click(screen.getByRole("checkbox", { name: "Case-sensitive" }));

    await waitFor(() => expect(lastListQuery(api).get("case_sensitive")).toBe("true"));
  });

  it("shows the missing-translation filter as off until a language is chosen", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary("/glossary?missing=fr");
    await screen.findByText("Hochschrank");
    const missing = screen.getByRole("combobox", { name: "Missing translation in" });
    expect(missing).toHaveTextContent("Missing in:French");

    await userEvent.click(missing);
    await userEvent.click(await screen.findByRole("option", { name: "— (show all)" }));

    await waitFor(() => expect(lastListQuery(api).get("missing")).toBeNull());
    expect(missing).toHaveTextContent("Missing in:—");
  });

  it("restores search and filters from the URL", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary(
      "/glossary?q=hoch&category=kitchen_term&missing=fr&do_not_translate=true" +
        "&case_sensitive=true&sort=en&order=desc&page=2",
    );

    await screen.findByText("Hochschrank");
    const query = lastListQuery(api);
    expect(Object.fromEntries(query)).toMatchObject({
      q: "hoch",
      category: "kitchen_term",
      missing: "fr",
      do_not_translate: "true",
      case_sensitive: "true",
      sort: "en",
      order: "desc",
      page: "2",
    });
    expect(screen.getByLabelText("Search terms in all languages")).toHaveValue("hoch");
  });

  it("ignores invalid URL values", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary("/glossary?category=colour&missing=xx&sort=text&page=-3");

    await screen.findByText("Hochschrank");
    const query = lastListQuery(api);
    expect(query.get("category")).toBeNull();
    expect(query.get("missing")).toBeNull();
    expect(query.get("sort")).toBe("de");
    expect(query.get("page")).toBe("1");
  });

  it("clears all filters", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary("/glossary?q=hoch&missing=fr");
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    await waitFor(() => {
      const query = lastListQuery(api);
      expect(query.get("q")).toBeNull();
      expect(query.get("missing")).toBeNull();
    });
    expect(screen.getByLabelText("Search terms in all languages")).toHaveValue("");
  });

  it("sorts by a language column and flips the order on a second click", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("button", { name: "English" }));
    await waitFor(() => expect(lastListQuery(api).get("sort")).toBe("en"));
    expect(lastListQuery(api).get("order")).toBe("asc");

    await userEvent.click(screen.getByRole("button", { name: "English" }));
    await waitFor(() => expect(lastListQuery(api).get("order")).toBe("desc"));
    expect(screen.getByRole("columnheader", { name: "English" })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
  });

  it("hides and remembers language columns", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("button", { name: /Languages \(7\/7\)/ }));
    await userEvent.click(await screen.findByRole("menuitemcheckbox", { name: "Danish" }));
    await userEvent.keyboard("{Escape}");

    expect(screen.queryByRole("columnheader", { name: "Danish" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Languages \(6\/7\)/ })).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("glossary.visibleLanguages")!)).not.toContain("da");
  });

  it("pages through results", async () => {
    const api = mockApi({
      ...baseRoutes,
      "GET /api/glossary": ({ query }) => ({
        body: page([HOCHSCHRANK], { total: 120, page: Number(query.get("page")) }),
      }),
    });
    renderGlossary();

    expect(await screen.findByText("1–50 of 120")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Next page" }));

    await waitFor(() => expect(lastListQuery(api).get("page")).toBe("2"));
    expect(await screen.findByText("51–100 of 120")).toBeInTheDocument();
  });

  it("shows an empty state for an empty glossary", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([]) } });
    renderGlossary();

    expect(await screen.findByText("The glossary is empty")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add first entry" })).toBeInTheDocument();
  });

  it("shows a no-results state when filters match nothing", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([]) } });
    renderGlossary("/glossary?q=xyz");

    expect(await screen.findByText("No entries match")).toBeInTheDocument();
  });

  it("shows an error with a working retry", async () => {
    let fail = true;
    mockApi({
      ...baseRoutes,
      "GET /api/glossary": () => (fail ? { status: 500, body: {} } : { body: page([HOCHSCHRANK]) }),
    });
    renderGlossary();

    expect(await screen.findByText("Could not load the glossary")).toBeInTheDocument();

    fail = false;
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Hochschrank")).toBeInTheDocument();
  });
});
