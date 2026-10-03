import { Columns3Icon, SearchIcon, XIcon } from "lucide-react";

import type { GlossaryCategory, Language, LanguageCode } from "@/api/client";
import { CATEGORY_STYLES } from "@/components/CategoryBadge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { GlossaryQuery } from "@/hooks/useGlossary";
import type { GlossaryFilterPatch } from "@/hooks/useGlossaryUrlState";

// Radix Select items cannot have an empty value, so "any" stands for "no filter".
const ANY = "any";

interface GlossaryToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  query: GlossaryQuery;
  onFiltersChange: (patch: GlossaryFilterPatch) => void;
  hasFilters: boolean;
  onClearFilters: () => void;
  languages: Language[];
  visibleLanguages: LanguageCode[];
  onVisibleLanguagesChange: (codes: LanguageCode[]) => void;
}

function FlagFilter({
  id,
  label,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center gap-2 px-1">
      <Checkbox id={id} checked={checked} onCheckedChange={(c) => onChange(c === true)} />
      <Label htmlFor={id} className="font-normal">
        {label}
      </Label>
    </div>
  );
}

export function GlossaryToolbar({
  search,
  onSearchChange,
  query,
  onFiltersChange,
  hasFilters,
  onClearFilters,
  languages,
  visibleLanguages,
  onVisibleLanguagesChange,
}: GlossaryToolbarProps) {
  function toggleLanguage(code: LanguageCode, visible: boolean) {
    const next = visible
      ? languages.map((l) => l.code).filter((c) => c === code || visibleLanguages.includes(c))
      : visibleLanguages.filter((c) => c !== code);
    if (next.length > 0) onVisibleLanguagesChange(next);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative w-full sm:w-72">
        <SearchIcon
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
        />
        <Input
          type="search"
          aria-label="Search terms in all languages"
          placeholder="Search in all languages…"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-8 pr-8 [&::-webkit-search-cancel-button]:hidden"
        />
        {search && (
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Clear search"
            className="absolute top-1/2 right-0.5 -translate-y-1/2"
            onClick={() => onSearchChange("")}
          >
            <XIcon />
          </Button>
        )}
      </div>

      <Select
        value={query.category ?? ANY}
        onValueChange={(v) =>
          onFiltersChange({ category: v === ANY ? undefined : (v as GlossaryCategory) })
        }
      >
        <SelectTrigger aria-label="Category" className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY}>All categories</SelectItem>
          {Object.entries(CATEGORY_STYLES).map(([value, style]) => (
            <SelectItem key={value} value={value}>
              {style.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Finds entries that still lack a translation in the chosen language. */}
      <Select
        // An empty value shows the "—" placeholder, i.e. no filter.
        value={query.missing ?? ""}
        onValueChange={(v) =>
          onFiltersChange({ missing: v === ANY ? undefined : (v as LanguageCode) })
        }
      >
        <SelectTrigger aria-label="Missing translation in" className="w-48">
          <span className="text-muted-foreground">Missing in:</span>
          <SelectValue placeholder="—" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY}>— (show all)</SelectItem>
          {languages.map((language) => (
            <SelectItem key={language.code} value={language.code}>
              {language.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <FlagFilter
        id="filter-do-not-translate"
        label="Do not translate"
        checked={query.doNotTranslate ?? false}
        onChange={(checked) => onFiltersChange({ doNotTranslate: checked })}
      />
      <FlagFilter
        id="filter-case-sensitive"
        label="Case-sensitive"
        checked={query.caseSensitive ?? false}
        onChange={(checked) => onFiltersChange({ caseSensitive: checked })}
      />

      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={onClearFilters}>
          <XIcon />
          Clear filters
        </Button>
      )}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="ml-auto">
            <Columns3Icon />
            Languages ({visibleLanguages.length}/{languages.length})
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Visible language columns</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {languages.map((language) => (
            <DropdownMenuCheckboxItem
              key={language.code}
              checked={visibleLanguages.includes(language.code)}
              // The last visible column cannot be hidden.
              disabled={visibleLanguages.length === 1 && visibleLanguages[0] === language.code}
              onCheckedChange={(checked) => toggleLanguage(language.code, checked)}
              onSelect={(e) => e.preventDefault()}
            >
              {language.name}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
