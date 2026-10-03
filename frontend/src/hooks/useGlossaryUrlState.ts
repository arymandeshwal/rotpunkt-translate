import { useSearchParams } from "react-router";

import type { GlossaryCategory } from "@/api/client";
import type { GlossaryQuery, SortField } from "@/hooks/useGlossary";
import { isLanguageCode } from "@/lib/languages";

export const PAGE_SIZE = 50;

const CATEGORIES: readonly GlossaryCategory[] = ["kitchen_term", "general", "product_name"];

function isCategory(value: string | null): value is GlossaryCategory {
  return CATEGORIES.includes(value as GlossaryCategory);
}

function isSortField(value: string | null): value is SortField {
  return value === "created_at" || value === "updated_at" || isLanguageCode(value);
}

export type GlossaryFilterPatch = Partial<
  Pick<GlossaryQuery, "q" | "category" | "doNotTranslate" | "caseSensitive" | "missing">
>;

// URL parameter names match the API's query parameters.
const FILTER_PARAMS = ["q", "category", "do_not_translate", "case_sensitive", "missing"] as const;

function flag(value: boolean | undefined) {
  return value ? "true" : undefined;
}

/**
 * Glossary list state (search, filters, sort, page) stored in the URL query string,
 * so views can be bookmarked and the back button works. Invalid values are ignored.
 */
export function useGlossaryUrlState() {
  const [params, setParams] = useSearchParams();

  const category = params.get("category");
  const missing = params.get("missing");
  const sort = params.get("sort");
  const page = Number(params.get("page"));

  const query: GlossaryQuery = {
    q: params.get("q") ?? undefined,
    category: isCategory(category) ? category : undefined,
    doNotTranslate: params.get("do_not_translate") === "true" ? true : undefined,
    caseSensitive: params.get("case_sensitive") === "true" ? true : undefined,
    missing: isLanguageCode(missing) ? missing : undefined,
    sort: isSortField(sort) ? sort : "de",
    order: params.get("order") === "desc" ? "desc" : "asc",
    page: Number.isInteger(page) && page > 0 ? page : 1,
    pageSize: PAGE_SIZE,
  };

  const hasFilters = Boolean(
    query.q || query.category || query.doNotTranslate || query.caseSensitive || query.missing,
  );

  function update(changes: Record<string, string | undefined>, { replace = false } = {}) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        for (const [key, value] of Object.entries(changes)) {
          if (value === undefined || value === "") next.delete(key);
          else next.set(key, value);
        }
        return next;
      },
      { replace },
    );
  }

  return {
    query,
    hasFilters,
    /** Changing a filter always returns to the first page. */
    setFilters(patch: GlossaryFilterPatch, options?: { replace?: boolean }) {
      const changes: Record<string, string | undefined> = { page: undefined };
      if ("q" in patch) changes.q = patch.q?.trim();
      if ("category" in patch) changes.category = patch.category;
      if ("doNotTranslate" in patch) changes.do_not_translate = flag(patch.doNotTranslate);
      if ("caseSensitive" in patch) changes.case_sensitive = flag(patch.caseSensitive);
      if ("missing" in patch) changes.missing = patch.missing;
      update(changes, options);
    },
    clearFilters() {
      update({
        ...Object.fromEntries(FILTER_PARAMS.map((name) => [name, undefined])),
        page: undefined,
      });
    },
    /** Clicking the active column flips the order; a new column starts ascending. */
    toggleSort(field: SortField) {
      const order = query.sort === field && query.order === "asc" ? "desc" : "asc";
      update({ sort: field, order, page: undefined });
    },
    setPage(next: number) {
      update({ page: next > 1 ? String(next) : undefined });
    },
  };
}
