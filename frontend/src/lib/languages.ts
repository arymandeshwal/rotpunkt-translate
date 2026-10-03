import type { LanguageCode } from "@/api/client";

// Keyed by LanguageCode so TypeScript flags a missing or unknown code when the API changes.
// Names and display order come from GET /api/languages; this is only for validating input.
const LANGUAGE_CODES: Record<LanguageCode, true> = {
  de: true,
  en: true,
  fr: true,
  nl: true,
  da: true,
  nb: true,
  es: true,
};

export const ALL_LANGUAGE_CODES = Object.keys(LANGUAGE_CODES) as LanguageCode[];

export function isLanguageCode(value: unknown): value is LanguageCode {
  return typeof value === "string" && value in LANGUAGE_CODES;
}
