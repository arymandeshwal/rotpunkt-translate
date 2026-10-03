import { LockIcon, Trash2Icon } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { toast } from "sonner";

import {
  ApiError,
  type GlossaryCategory,
  type GlossaryEntry,
  type GlossaryEntryCreate,
  type Language,
  type LanguageCode,
} from "@/api/client";
import { CATEGORY_STYLES } from "@/components/CategoryBadge";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { useCreateEntry, useDeleteEntry, useUpdateEntry } from "@/hooks/useGlossary";

interface FormState {
  category: GlossaryCategory;
  doNotTranslate: boolean;
  caseSensitive: boolean;
  description: string;
  terms: Partial<Record<LanguageCode, string>>;
}

type FieldErrors = Partial<Record<LanguageCode, string>>;

interface Conflict {
  language: LanguageCode;
  text: string;
  entry_id: number;
}

function initialState(entry: GlossaryEntry | null): FormState {
  return {
    // Same default as the API (GlossaryEntryCreate.category).
    category: entry?.category ?? "general",
    doNotTranslate: entry?.do_not_translate ?? false,
    caseSensitive: entry?.case_sensitive ?? false,
    description: entry?.description ?? "",
    terms: Object.fromEntries(entry?.terms.map((t) => [t.language, t.text]) ?? []),
  };
}

/** The language whose term a protected entry keeps: the first filled one, else the first. */
function protectedLanguage(form: FormState, languages: Language[]): LanguageCode {
  const filled = languages.find((l) => form.terms[l.code]?.trim());
  return (filled ?? languages[0])!.code;
}

function toRequest(form: FormState, languages: Language[]): GlossaryEntryCreate {
  const codes = form.doNotTranslate
    ? [protectedLanguage(form, languages)]
    : languages.map((l) => l.code);
  return {
    category: form.category,
    do_not_translate: form.doNotTranslate,
    case_sensitive: form.caseSensitive,
    description: form.description.trim() || null,
    terms: codes
      .map((code) => ({ language: code, text: form.terms[code]?.trim() ?? "" }))
      .filter((t) => t.text),
  };
}

function describeError(error: unknown) {
  if (error instanceof ApiError && error.status === 409) {
    const detail = (error.body as { detail?: { conflicts?: Conflict[] } } | undefined)?.detail;
    const fields: FieldErrors = {};
    for (const c of detail?.conflicts ?? []) {
      fields[c.language] = `Already in the glossary as “${c.text}” (entry #${c.entry_id})`;
    }
    return { fields, form: Object.keys(fields).length ? null : "This term already exists." };
  }
  if (error instanceof ApiError && error.status === 422) {
    const detail = (error.body as { detail?: { msg: string }[] } | undefined)?.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join(" ") : null;
    return { fields: {}, form: message ?? "Some fields are invalid." };
  }
  return { fields: {}, form: "Could not save the entry. Please try again." };
}

interface EntryPanelProps {
  /** null creates a new entry. */
  entry: GlossaryEntry | null;
  languages: Language[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EntryPanel({ entry, languages, open, onOpenChange }: EntryPanelProps) {
  const [form, setForm] = useState(() => initialState(entry));
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [initial] = useState(() => toRequest(initialState(entry), languages));

  const createEntry = useCreateEntry();
  const updateEntry = useUpdateEntry();
  const deleteEntry = useDeleteEntry();
  const saving = createEntry.isPending || updateEntry.isPending;

  const isNew = entry === null;
  const lockedLanguage = protectedLanguage(form, languages);
  const title = entry?.terms[0]?.text;

  // Compared as the request it would send, so whitespace-only edits don't count.
  const isDirty = JSON.stringify(toRequest(form, languages)) !== JSON.stringify(initial);

  /** Close via Cancel, ✕, Escape or a click outside: ask first if there are unsaved edits. */
  function requestClose() {
    if (isDirty) setConfirmDiscard(true);
    else onOpenChange(false);
  }

  function update(patch: Partial<FormState>) {
    setForm((current) => ({ ...current, ...patch }));
  }

  function setTerm(code: LanguageCode, text: string) {
    setForm((current) => ({ ...current, terms: { ...current.terms, [code]: text } }));
    setFieldErrors((current) => ({ ...current, [code]: undefined }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const body = toRequest(form, languages);
    if (body.terms.length === 0) {
      setFormError("Enter the term in at least one language.");
      return;
    }
    setFieldErrors({});
    setFormError(null);
    try {
      const saved = isNew
        ? await createEntry.mutateAsync(body)
        : await updateEntry.mutateAsync({ id: entry.id, body });
      toast.success(`${isNew ? "Added" : "Saved"} “${saved.terms[0]?.text}”`);
      onOpenChange(false);
    } catch (error) {
      const { fields, form: message } = describeError(error);
      setFieldErrors(fields);
      setFormError(message);
    }
  }

  async function handleDelete() {
    if (!entry) return;
    try {
      await deleteEntry.mutateAsync(entry.id);
      toast.success(`Deleted “${title}”`);
      onOpenChange(false);
    } catch {
      setFormError("Could not delete the entry. Please try again.");
    }
  }

  return (
    <Sheet open={open} onOpenChange={(next) => (next ? onOpenChange(true) : requestClose())}>
      <SheetContent className="w-full sm:max-w-md">
        <form onSubmit={handleSubmit} className="flex h-full flex-col" noValidate>
          <SheetHeader>
            <SheetTitle>{isNew ? "New glossary entry" : `Edit “${title}”`}</SheetTitle>
            <SheetDescription>
              {isNew
                ? "Add a term and its translations."
                : "Change the term, its translations or how it is treated."}
            </SheetDescription>
          </SheetHeader>

          <div className="flex-1 space-y-5 overflow-y-auto px-4 pb-4">
            {formError && (
              <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-destructive">
                {formError}
              </p>
            )}

            <div className="space-y-2">
              <Label htmlFor="entry-category">Category</Label>
              <Select
                value={form.category}
                onValueChange={(v) => update({ category: v as GlossaryCategory })}
              >
                <SelectTrigger id="entry-category" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CATEGORY_STYLES).map(([value, style]) => (
                    <SelectItem key={value} value={value}>
                      {style.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <div className="flex items-start gap-2">
                <Checkbox
                  id="entry-dnt"
                  checked={form.doNotTranslate}
                  onCheckedChange={(checked) => update({ doNotTranslate: checked === true })}
                />
                <div className="grid gap-1">
                  <Label htmlFor="entry-dnt">Do not translate</Label>
                  <p className="text-xs text-muted-foreground">
                    Product names, brands, colours: used unchanged in every language.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Checkbox
                  id="entry-case"
                  checked={form.caseSensitive}
                  onCheckedChange={(checked) => update({ caseSensitive: checked === true })}
                />
                <div className="grid gap-1">
                  <Label htmlFor="entry-case">Case-sensitive</Label>
                  <p className="text-xs text-muted-foreground">
                    Only match the exact capitalisation, e.g. for item codes.
                  </p>
                </div>
              </div>
            </div>

            <fieldset className="space-y-3">
              <legend className="mb-2 text-sm font-medium">
                {form.doNotTranslate ? "Term" : "Terms"}
              </legend>
              {form.doNotTranslate ? (
                <TermField
                  id={`entry-term-${lockedLanguage}`}
                  label={
                    <span className="inline-flex items-center gap-1.5">
                      <LockIcon aria-hidden className="size-3.5" />
                      Used in every language
                    </span>
                  }
                  value={form.terms[lockedLanguage] ?? ""}
                  error={fieldErrors[lockedLanguage]}
                  onChange={(text) => setTerm(lockedLanguage, text)}
                />
              ) : (
                languages.map((language) => (
                  <TermField
                    key={language.code}
                    id={`entry-term-${language.code}`}
                    label={language.name}
                    value={form.terms[language.code] ?? ""}
                    error={fieldErrors[language.code]}
                    onChange={(text) => setTerm(language.code, text)}
                  />
                ))
              )}
            </fieldset>

            <div className="space-y-2">
              <Label htmlFor="entry-description">Description</Label>
              <Textarea
                id="entry-description"
                rows={3}
                maxLength={2000}
                placeholder="Context for translators and the AI, e.g. what the item is."
                value={form.description}
                onChange={(e) => update({ description: e.target.value })}
              />
            </div>
          </div>

          <SheetFooter className="flex-row border-t">
            {!isNew && (
              <Button
                type="button"
                variant="ghost"
                className="mr-auto text-destructive hover:text-destructive"
                onClick={() => setConfirmDelete(true)}
              >
                <Trash2Icon />
                Delete
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              className={isNew ? "ml-auto" : undefined}
              onClick={requestClose}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : isNew ? "Add entry" : "Save"}
            </Button>
          </SheetFooter>
        </form>

        <ConfirmDialog
          open={confirmDelete}
          onOpenChange={setConfirmDelete}
          title={`Delete “${title}”?`}
          description="The entry and all its translations are removed from the glossary. This cannot be undone."
          confirmLabel="Delete"
          destructive
          onConfirm={handleDelete}
        />

        <ConfirmDialog
          open={confirmDiscard}
          onOpenChange={setConfirmDiscard}
          title="Discard unsaved changes?"
          description="Your changes to this entry have not been saved."
          confirmLabel="Discard"
          cancelLabel="Keep editing"
          destructive
          onConfirm={() => onOpenChange(false)}
        />
      </SheetContent>
    </Sheet>
  );
}

interface TermFieldProps {
  id: string;
  label: ReactNode;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}

function TermField({ id, label, value, error, onChange }: TermFieldProps) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id} className="font-normal text-muted-foreground">
        {label}
      </Label>
      <Input
        id={id}
        value={value}
        maxLength={255}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
      {error && (
        <p id={`${id}-error`} className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
