import { BookOpenIcon, PlusIcon, SearchXIcon } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import type { GlossaryEntry, LanguageCode } from "@/api/client";
import { EntryPanel } from "@/components/glossary/EntryPanel";
import { GlossaryPagination } from "@/components/glossary/GlossaryPagination";
import { GlossaryTable, GlossaryTableSkeleton } from "@/components/glossary/GlossaryTable";
import { GlossaryToolbar } from "@/components/glossary/GlossaryToolbar";
import { Button } from "@/components/ui/button";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useGlossaryList, useLanguages } from "@/hooks/useGlossary";
import { useGlossaryUrlState } from "@/hooks/useGlossaryUrlState";
import { useStoredState } from "@/hooks/useStoredState";
import { ALL_LANGUAGE_CODES, isLanguageCode } from "@/lib/languages";

export const SEARCH_DEBOUNCE_MS = 300;

function isLanguageList(value: unknown): value is LanguageCode[] {
  return Array.isArray(value) && value.length > 0 && value.every(isLanguageCode);
}

type PanelState = { open: false } | { open: true; entry: GlossaryEntry | null; key: string };

export function GlossaryPage() {
  const { query, hasFilters, setFilters, clearFilters, toggleSort, setPage } =
    useGlossaryUrlState();
  const languagesQuery = useLanguages();
  const list = useGlossaryList(query);

  const [visibleLanguages, setVisibleLanguages] = useStoredState(
    "glossary.visibleLanguages",
    ALL_LANGUAGE_CODES,
    isLanguageList,
  );
  const [panel, setPanel] = useState<PanelState>({ open: false });

  // The search box updates immediately; the URL (and the request) follow after a pause.
  const [search, setSearch] = useState(query.q ?? "");
  const debouncedSearch = useDebouncedValue(search, SEARCH_DEBOUNCE_MS);
  useEffect(() => {
    if (debouncedSearch.trim() !== (query.q ?? "")) {
      setFilters({ q: debouncedSearch }, { replace: true });
    }
    // Only react to the user's typing, not to URL changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  // Deleting the last entry on a page leaves it empty: step back to the last real page.
  const lastPage = Math.max(1, Math.ceil((list.data?.total ?? 0) / query.pageSize));
  useEffect(() => {
    if (list.data && query.page > lastPage) setPage(lastPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [list.data, query.page, lastPage]);

  function handleClearFilters() {
    setSearch("");
    clearFilters();
  }

  const languages = languagesQuery.data ?? [];
  const shownLanguages = languages.filter((l) => visibleLanguages.includes(l.code));
  const total = list.data?.total ?? 0;

  function openEntry(entry: GlossaryEntry | null) {
    setPanel({ open: true, entry, key: entry ? `edit-${entry.id}` : `new-${Date.now()}` });
  }

  let content;
  if (list.isError || languagesQuery.isError) {
    content = (
      <EmptyState
        icon={<SearchXIcon />}
        title="Could not load the glossary"
        text="The server did not respond. Check that the backend is running."
        action={
          <Button
            variant="outline"
            onClick={() => {
              void list.refetch();
              void languagesQuery.refetch();
            }}
          >
            Retry
          </Button>
        }
      />
    );
  } else if (!list.data || !languagesQuery.data) {
    content = <GlossaryTableSkeleton columns={shownLanguages.length + 2 || 9} />;
  } else if (total === 0 && !hasFilters) {
    content = (
      <EmptyState
        icon={<BookOpenIcon />}
        title="The glossary is empty"
        text="Add company terms, their translations and protected product names."
        action={
          <Button onClick={() => openEntry(null)}>
            <PlusIcon />
            Add first entry
          </Button>
        }
      />
    );
  } else if (list.data.items.length === 0) {
    content = (
      <EmptyState
        icon={<SearchXIcon />}
        title="No entries match"
        text="Try a different search or remove some filters."
        action={
          <Button variant="outline" onClick={handleClearFilters}>
            Clear filters
          </Button>
        }
      />
    );
  } else {
    content = (
      <GlossaryTable
        entries={list.data.items}
        languages={shownLanguages}
        sort={query.sort}
        order={query.order}
        onSort={toggleSort}
        onOpen={openEntry}
      />
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Glossary</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Company terms, translations and protected product names.
            {list.data && ` ${total} ${total === 1 ? "entry" : "entries"}${hasFilters ? " match" : ""}.`}
          </p>
        </div>
        <Button onClick={() => openEntry(null)}>
          <PlusIcon />
          New entry
        </Button>
      </div>

      <GlossaryToolbar
        search={search}
        onSearchChange={setSearch}
        query={query}
        onFiltersChange={setFilters}
        hasFilters={hasFilters || search !== ""}
        onClearFilters={handleClearFilters}
        languages={languages}
        visibleLanguages={visibleLanguages}
        onVisibleLanguagesChange={setVisibleLanguages}
      />

      <div className="rounded-lg border bg-background">{content}</div>

      {list.data && total > 0 && (
        <GlossaryPagination
          page={query.page}
          pageSize={query.pageSize}
          total={total}
          onPageChange={setPage}
        />
      )}

      {panel.open && (
        <EntryPanel
          key={panel.key}
          entry={panel.entry}
          languages={languages}
          open
          onOpenChange={(open) => {
            if (!open) setPanel({ open: false });
          }}
        />
      )}
    </section>
  );
}

function EmptyState({
  icon,
  title,
  text,
  action,
}: {
  icon: ReactNode;
  title: string;
  text: string;
  action: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-16 text-center">
      <div className="text-muted-foreground [&>svg]:size-8">{icon}</div>
      <h2 className="font-medium">{title}</h2>
      <p className="max-w-sm text-sm text-muted-foreground">{text}</p>
      <div className="mt-2">{action}</div>
    </div>
  );
}
