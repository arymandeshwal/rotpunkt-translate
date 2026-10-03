import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { AppRoutes } from "@/App";
import type { GlossaryEntry } from "@/api/client";
import { Toaster } from "@/components/ui/sonner";
import { HOCHSCHRANK, ZEROX, baseRoutes, page } from "@/test/glossaryFixtures";
import { mockApi } from "@/test/mockApi";
import { renderWithProviders } from "@/test/render";

function renderGlossary() {
  return renderWithProviders(
    <>
      <AppRoutes />
      <Toaster />
    </>,
    { route: "/glossary" },
  );
}

function saved(body: unknown, id = 99): GlossaryEntry {
  const b = body as Omit<GlossaryEntry, "id" | "created_at" | "updated_at">;
  return { ...HOCHSCHRANK, ...b, id, description: b.description ?? null };
}

async function openRow(text: string) {
  await userEvent.click((await screen.findAllByText(text))[0]!);
  return screen.findByRole("dialog");
}

describe("Entry panel: editing", () => {
  it("opens with the entry's values when a row is clicked", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();

    const panel = await openRow("Hochschrank");

    expect(within(panel).getByRole("heading", { name: "Edit “Hochschrank”" })).toBeInTheDocument();
    expect(within(panel).getByLabelText("German")).toHaveValue("Hochschrank");
    expect(within(panel).getByLabelText("English")).toHaveValue("tall unit");
    expect(within(panel).getByLabelText("French")).toHaveValue("");
    expect(within(panel).getByLabelText("Description")).toHaveValue(
      "Floor-standing cabinet at full room height",
    );
    expect(within(panel).getByRole("combobox", { name: "Category" })).toHaveTextContent(
      "Kitchen term",
    );
  });

  it("opens from the keyboard", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();

    (await screen.findByRole("row", { name: /Edit Hochschrank/ })).focus();
    await userEvent.keyboard("{Enter}");

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("saves all fields with PATCH, refreshes the list and closes", async () => {
    const api = mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "PATCH /api/glossary/:id": ({ body }) => ({ body: saved(body, 1) }),
    });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.clear(within(panel).getByLabelText("English"));
    await userEvent.type(within(panel).getByLabelText("English"), "tall cabinet");
    await userEvent.type(within(panel).getByLabelText("French"), "colonne");
    await userEvent.click(within(panel).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const [request] = api.to("/api/glossary/1", "PATCH");
    expect(request!.body).toEqual({
      category: "kitchen_term",
      do_not_translate: false,
      case_sensitive: false,
      description: "Floor-standing cabinet at full room height",
      terms: [
        { language: "de", text: "Hochschrank" },
        { language: "en", text: "tall cabinet" },
        { language: "fr", text: "colonne" },
      ],
    });
    expect(await screen.findByText("Saved “Hochschrank”")).toBeInTheDocument();
    await waitFor(() => expect(api.to("/api/glossary").length).toBeGreaterThan(1));
  });

  it("removes a translation by clearing its field", async () => {
    const api = mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "PATCH /api/glossary/:id": ({ body }) => ({ body: saved(body, 1) }),
    });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.clear(within(panel).getByLabelText("English"));
    await userEvent.click(within(panel).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(api.to("/api/glossary/1", "PATCH")).toHaveLength(1));
    expect(api.to("/api/glossary/1", "PATCH")[0]!.body).toMatchObject({
      terms: [{ language: "de", text: "Hochschrank" }],
    });
  });

  it("shows a duplicate error next to the conflicting language and stays open", async () => {
    mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "PATCH /api/glossary/:id": {
        status: 409,
        body: {
          detail: {
            message: "One or more terms already exist in the glossary",
            conflicts: [{ language: "en", text: "Tall Cabinet", entry_id: 7 }],
          },
        },
      },
    });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.clear(within(panel).getByLabelText("English"));
    await userEvent.type(within(panel).getByLabelText("English"), "tall cabinet");
    await userEvent.click(within(panel).getByRole("button", { name: "Save" }));

    const english = within(panel).getByLabelText("English");
    await waitFor(() => expect(english).toHaveAttribute("aria-invalid", "true"));
    expect(english).toHaveAccessibleDescription(
      "Already in the glossary as “Tall Cabinet” (entry #7)",
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await userEvent.type(english, "s");
    expect(english).not.toHaveAttribute("aria-invalid");
  });

  it("shows server validation messages", async () => {
    mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "PATCH /api/glossary/:id": {
        status: 422,
        body: { detail: [{ loc: ["body", "terms"], msg: "Something is off", type: "value_error" }] },
      },
    });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.click(within(panel).getByRole("button", { name: "Save" }));

    expect(await within(panel).findByRole("alert")).toHaveTextContent("Something is off");
  });

});

describe("Entry panel: unsaved changes", () => {
  it("closes straight away when nothing was changed", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.click(within(panel).getByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("does not count whitespace-only edits as changes", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.type(within(panel).getByLabelText("French"), "   ");
    await userEvent.click(within(panel).getByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it.each([
    ["Cancel", () => userEvent.click(screen.getByRole("button", { name: "Cancel" }))],
    ["the close button", () => userEvent.click(screen.getByRole("button", { name: "Close" }))],
    ["Escape", () => userEvent.keyboard("{Escape}")],
  ])("asks before discarding changes via %s", async (_, close) => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    const panel = await openRow("Hochschrank");
    await userEvent.type(within(panel).getByLabelText("French"), "colonne");

    await close();

    const confirm = await screen.findByRole("alertdialog", { name: "Discard unsaved changes?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Discard" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(api.requests.filter((r) => r.method !== "GET")).toEqual([]);
  });

  it("keeps the panel and the edits when the user keeps editing", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    const panel = await openRow("Hochschrank");
    await userEvent.type(within(panel).getByLabelText("French"), "colonne");

    await userEvent.click(within(panel).getByRole("button", { name: "Cancel" }));
    const confirm = await screen.findByRole("alertdialog");
    await userEvent.click(within(confirm).getByRole("button", { name: "Keep editing" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(within(screen.getByRole("dialog")).getByLabelText("French")).toHaveValue("colonne");
  });

  it("does not ask after a successful save", async () => {
    mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "PATCH /api/glossary/:id": ({ body }) => ({ body: saved(body, 1) }),
    });
    renderGlossary();
    const panel = await openRow("Hochschrank");
    await userEvent.type(within(panel).getByLabelText("French"), "colonne");

    await userEvent.click(within(panel).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
});

describe("Entry panel: creating", () => {
  it("creates an entry with POST", async () => {
    const api = mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "POST /api/glossary": ({ body }) => ({ status: 201, body: saved(body) }),
    });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("button", { name: "New entry" }));
    const panel = await screen.findByRole("dialog");
    expect(within(panel).getByRole("heading", { name: "New glossary entry" })).toBeInTheDocument();

    await userEvent.type(within(panel).getByLabelText("German"), "  Kochfeld ");
    await userEvent.type(within(panel).getByLabelText("English"), "hob");
    await userEvent.type(within(panel).getByLabelText("Description"), "Cooking surface");
    await userEvent.click(within(panel).getByRole("button", { name: "Add entry" }));

    await waitFor(() => expect(api.to("/api/glossary", "POST")).toHaveLength(1));
    expect(api.to("/api/glossary", "POST")[0]!.body).toEqual({
      category: "general",
      do_not_translate: false,
      case_sensitive: false,
      description: "Cooking surface",
      terms: [
        { language: "de", text: "Kochfeld" },
        { language: "en", text: "hob" },
      ],
    });
    expect(await screen.findByText("Added “Kochfeld”")).toBeInTheDocument();
  });

  it("requires at least one term before sending anything", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("button", { name: "New entry" }));
    const panel = await screen.findByRole("dialog");
    await userEvent.type(within(panel).getByLabelText("German"), "   ");
    await userEvent.click(within(panel).getByRole("button", { name: "Add entry" }));

    expect(within(panel).getByRole("alert")).toHaveTextContent(
      "Enter the term in at least one language.",
    );
    expect(api.to("/api/glossary", "POST")).toEqual([]);
  });

  it("is reachable from the empty state", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([]) } });
    renderGlossary();

    await userEvent.click(await screen.findByRole("button", { name: "Add first entry" }));

    expect(await screen.findByRole("heading", { name: "New glossary entry" })).toBeInTheDocument();
  });

  it("starts empty again after a previous entry was open", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    let panel = await openRow("Hochschrank");
    await userEvent.click(within(panel).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: "New entry" }));
    panel = await screen.findByRole("dialog");

    expect(within(panel).getByLabelText("German")).toHaveValue("");
  });
});

describe("Entry panel: do not translate", () => {
  it("shows a single term field for a protected entry", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([ZEROX]) } });
    renderGlossary();
    const panel = await openRow("Zerox HPL XT");

    expect(within(panel).getByLabelText("Used in every language")).toHaveValue("Zerox HPL XT");
    expect(within(panel).queryByLabelText("English")).not.toBeInTheDocument();
  });

  it("keeps only the first filled term when switched on, and restores the rest when off", async () => {
    const api = mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "PATCH /api/glossary/:id": ({ body }) => ({ body: saved(body, 1) }),
    });
    renderGlossary();
    const panel = await openRow("Hochschrank");
    const dnt = within(panel).getByRole("checkbox", { name: "Do not translate" });

    await userEvent.click(dnt);
    expect(within(panel).getByLabelText("Used in every language")).toHaveValue("Hochschrank");

    await userEvent.click(dnt);
    expect(within(panel).getByLabelText("English")).toHaveValue("tall unit");

    await userEvent.click(dnt);
    await userEvent.click(within(panel).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(api.to("/api/glossary/1", "PATCH")).toHaveLength(1));
    expect(api.to("/api/glossary/1", "PATCH")[0]!.body).toMatchObject({
      do_not_translate: true,
      terms: [{ language: "de", text: "Hochschrank" }],
    });
  });
});

describe("Entry panel: deleting", () => {
  it("deletes after confirmation", async () => {
    const api = mockApi({
      ...baseRoutes,
      "GET /api/glossary": { body: page([HOCHSCHRANK]) },
      "DELETE /api/glossary/:id": { status: 204 },
    });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.click(within(panel).getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Delete “Hochschrank”?" });
    await userEvent.click(within(confirm).getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(api.to("/api/glossary/1", "DELETE")).toHaveLength(1));
    expect(await screen.findByText("Deleted “Hochschrank”")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("does nothing when the confirmation is cancelled", async () => {
    const api = mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    const panel = await openRow("Hochschrank");

    await userEvent.click(within(panel).getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("alertdialog");
    await userEvent.click(within(confirm).getByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(api.to("/api/glossary/1", "DELETE")).toEqual([]);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("is not offered for a new entry", async () => {
    mockApi({ ...baseRoutes, "GET /api/glossary": { body: page([HOCHSCHRANK]) } });
    renderGlossary();
    await screen.findByText("Hochschrank");

    await userEvent.click(screen.getByRole("button", { name: "New entry" }));
    const panel = await screen.findByRole("dialog");

    expect(within(panel).queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
  });
});
