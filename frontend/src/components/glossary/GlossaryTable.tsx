import { ArrowDownIcon, ArrowUpDownIcon, ArrowUpIcon, LockIcon } from "lucide-react";

import type { GlossaryEntry, Language, LanguageCode } from "@/api/client";
import { CategoryBadge } from "@/components/CategoryBadge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SortField } from "@/hooks/useGlossary";
import { cn } from "@/lib/utils";

// The first column stays in view while the table scrolls sideways.
const STICKY = "sticky left-0 z-10 bg-background";

interface GlossaryTableProps {
  entries: GlossaryEntry[];
  languages: Language[];
  sort: SortField;
  order: "asc" | "desc";
  onSort: (field: SortField) => void;
  onOpen: (entry: GlossaryEntry) => void;
}

function SortIcon({ active, order }: { active: boolean; order: "asc" | "desc" }) {
  if (!active) return <ArrowUpDownIcon aria-hidden className="size-3.5 opacity-40" />;
  return order === "asc" ? (
    <ArrowUpIcon aria-hidden className="size-3.5" />
  ) : (
    <ArrowDownIcon aria-hidden className="size-3.5" />
  );
}

function TermCell({ entry, language }: { entry: GlossaryEntry; language: LanguageCode }) {
  if (entry.do_not_translate) {
    // A protected term is used unchanged in every language.
    return (
      <span className="inline-flex items-center gap-1.5">
        <LockIcon aria-label="Do not translate" className="size-3.5 text-muted-foreground" />
        {entry.terms[0]?.text}
      </span>
    );
  }
  const term = entry.terms.find((t) => t.language === language);
  if (term) return <>{term.text}</>;
  return (
    <span className="rounded border border-dashed px-1.5 py-0.5 text-xs text-muted-foreground">
      missing
    </span>
  );
}

export function GlossaryTable({
  entries,
  languages,
  sort,
  order,
  onSort,
  onOpen,
}: GlossaryTableProps) {
  return (
    <Table className="min-w-max">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {languages.map((language, index) => (
            <TableHead
              key={language.code}
              className={cn("min-w-40", index === 0 && STICKY)}
              aria-sort={
                sort === language.code ? (order === "asc" ? "ascending" : "descending") : "none"
              }
            >
              <button
                type="button"
                className="inline-flex items-center gap-1 hover:text-foreground"
                onClick={() => onSort(language.code)}
              >
                {language.name}
                <SortIcon active={sort === language.code} order={order} />
              </button>
            </TableHead>
          ))}
          <TableHead>Category</TableHead>
          <TableHead className="min-w-64">Description</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => (
          <TableRow
            key={entry.id}
            tabIndex={0}
            aria-label={`Edit ${entry.terms[0]?.text ?? "entry"}`}
            className="cursor-pointer focus-visible:bg-muted focus-visible:outline-none"
            onClick={() => onOpen(entry)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onOpen(entry);
              }
            }}
          >
            {languages.map((language, index) => (
              <TableCell key={language.code} className={cn(index === 0 && STICKY)}>
                <TermCell entry={entry} language={language.code} />
              </TableCell>
            ))}
            <TableCell>
              <CategoryBadge category={entry.category} />
            </TableCell>
            <TableCell className="max-w-md whitespace-normal text-muted-foreground">
              {entry.description}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function GlossaryTableSkeleton({ columns }: { columns: number }) {
  return (
    <div aria-label="Loading glossary" role="status" className="space-y-2 py-2">
      {Array.from({ length: 6 }, (_, row) => (
        <div key={row} className="flex gap-4">
          {Array.from({ length: columns }, (_, col) => (
            <Skeleton key={col} className="h-6 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
