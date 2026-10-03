import type { GlossaryEntry, GlossaryPage, Language } from "@/api/client";

export const LANGUAGES: Language[] = [
  { code: "de", name: "German" },
  { code: "en", name: "English" },
  { code: "fr", name: "French" },
  { code: "nl", name: "Dutch" },
  { code: "da", name: "Danish" },
  { code: "nb", name: "Norwegian (Bokmål)" },
  { code: "es", name: "Spanish" },
];

const timestamps = { created_at: "2026-10-03T10:00:00Z", updated_at: "2026-10-03T10:00:00Z" };

export const HOCHSCHRANK: GlossaryEntry = {
  id: 1,
  category: "kitchen_term",
  do_not_translate: false,
  case_sensitive: false,
  description: "Floor-standing cabinet at full room height",
  terms: [
    { language: "de", text: "Hochschrank" },
    { language: "en", text: "tall unit" },
  ],
  ...timestamps,
};

export const ZEROX: GlossaryEntry = {
  id: 2,
  category: "product_name",
  do_not_translate: true,
  case_sensitive: false,
  description: null,
  terms: [{ language: "de", text: "Zerox HPL XT" }],
  ...timestamps,
};

export function page(items: GlossaryEntry[], overrides: Partial<GlossaryPage> = {}): GlossaryPage {
  return { items, total: items.length, page: 1, page_size: 50, ...overrides };
}

export const baseRoutes = {
  "GET /api/health": { body: { status: "ok", database: "ok" } },
  "GET /api/languages": { body: LANGUAGES },
};
