# Rotpunkt Translate – Roadmap

AI-assisted translation tool for kitchen-industry documents, built from the client
specification *"Übersetzungstool für Rotpunkt Küchen"*.

**Goal:** every feature works, the UI is intuitive, the product is scalable.

| Part | Focus | Status |
|---|---|---|
| **Part 1 – MVP** | Core flow: upload PDF → translate with glossary → preview with highlighting → QA | 🟡 In progress (steps 0–2 done) |
| **Part 2 – Full feature set** | Every remaining feature from the specification, each with tests | ⬜ Not started |
| **Part 3 – Scale** | Find bottlenecks, make it scalable | ⬜ Not started |

Legend: ✅ done · 🟡 in progress / done but not committed · ⬜ not started · ⏸ deferred

_Last updated: 2026-10-05_

---

## Working agreements

- Each step is split into small sub-parts; **every sub-part ships with tests**.
- The user reviews every change **before** it is committed; commit messages stay short.
- Data model, architecture, API and UI are designed **per feature**, not upfront.
- Heuristics are justified by **measurements on real documents**, not guesses
  (see the Rotpunkt sample PDFs in [`samples/SOURCES.md`](../samples/SOURCES.md)).
- Every Python function has a Google-style docstring (`Args`, `Returns`, `Raises`).

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL |
| PDF parsing | PyMuPDF (AGPL, accepted) |
| Frontend | React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, openapi-fetch (types generated from the API) |
| Translation | DeepL (free API) and an LLM (Claude) behind one provider interface |
| Testing | pytest (real Postgres), Vitest + Testing Library, Playwright (planned) |
| Tooling | uv, ruff, mypy strict, ESLint, Docker Compose, GitHub Actions |

---

## Part 1 – MVP

**Scope (feature IDs from the specification breakdown):**
A2, B3 (PDF), B5, B6, B7, B8, C1, C2, D1, D2, D4, E2, F1–F5, G5, H1–H3, I1, I2, P1.

> Scope change (2026-10-03): Part 1 ingests **PDF only**, because Rotpunkt's public
> documents are all PDFs. DOCX/XLSX (B1, B2) moved to Part 2.

| # | Step | Features | Status |
|---|---|---|---|
| 0 | **Skeleton** – Docker Compose, FastAPI health check, React shell, Postgres, CI | – | ✅ `18fc73b` |
| 1 | **Glossary** | H1, H2, H3 | ✅ |
| 2 | **PDF parser** | B3, B5, B6 | ✅ |
| 3 | **Upload + project** | B3, B8, A2, B7, C1 | ⬜ next |
| 4 | **Translation providers** | D1, D2, C2 | ⬜ |
| 5 | **Glossary enforcement** | D4 | ⬜ |
| 6 | **Translation job** (background, batched, status) | – | ⬜ |
| 7 | **Term highlighting** | F1, F2, then F3–F5 | ⬜ |
| 8 | **Side-by-side preview** | E2 | ⬜ |
| 9 | **Re-translate segment** | G5 | ⬜ |
| 10 | **Quality checks** | I1, I2 | ⬜ |
| 11 | **End-to-end test** (Playwright) | – | ⬜ |

### Step 1 – Glossary ✅

| Sub-part | Content | Status |
|---|---|---|
| 1a | Data model: one entry per concept, one term per language; DB constraints (supported languages, no blanks, case-insensitive uniqueness per language) | ✅ `736a715` |
| 1b | Read API: list, search in all languages, filters, sorting, paging, `GET /api/languages` | ✅ `7c6ffc5` |
| 1c | Write API: create / update / delete, 409 with conflicting entries, 422 validation | ✅ `7c6ffc5` |
| 1d | Seed data: 46 Rotpunkt terms and product names (`python -m app.seed`) | ✅ `0fb55d7` |
| 1e | Frontend groundwork: generated API types, typed client, shadcn/ui | ✅ `0fb55d7` |
| 1f | Glossary table: all languages, search, filters (category, missing in, do not translate, case-sensitive), sorting, paging, state in URL | ✅ `6217c59` |
| 1g | Edit side panel: create/edit/delete, duplicate errors per field, unsaved-changes confirmation | ✅ `6217c59` |

Decisions: concept-based entries · 7 languages (DE, EN, FR, NL, DA, NB, ES) · categories
kitchen term / product name / general · "do not translate" entries have exactly one term ·
`PATCH terms` replaces the full set · frontend and backend share the default category (general).

### Step 2 – PDF parser 🟡

| Sub-part | Content | Status |
|---|---|---|
| 2a | Extraction: every line with position, font size, bold; only invisible normalization (NFC, soft hyphens, control characters) | ✅ `b77de62` |
| 2b | Layout: fragments, list items (bullets + drawn checkboxes), paragraphs, XY-cut reading order, headings by font size | ✅ `f31da36` |
| – | Review against the sample PDFs: ablation + threshold sweeps, 4 bugs fixed, unused heuristics removed, docstrings | ✅ `b368dfe` |
| 2c | Rejecting bad files: empty, corrupt, password-protected, too large, scanned (no OCR); single scanned pages flagged `no_text_layer` | ✅ |
| 2d | Regression tests on the real Rotpunkt PDFs (skipped when not downloaded) | ✅ |

**Verification done**
- 18 hand-verified checks on the 7 sample PDFs; every threshold sits in a safe range.
- Manual review of **all 78 sample pages as images** vs. parser output: **no missing text**.
- DeepL experiment (3.3k characters): DeepL repairs hyphenation and soft-hyphen splits by itself.

**Decisions**
- Everything is translated, including headers, footers and page numbers.
- One segment = one heading, paragraph or list item.
- No dehyphenation in the parser (DeepL handles it).
- **One source language → one target language.** Text in other languages is not translated.

**Known limitations (accepted for now)**
- Reading order of forms/tables: questions are grouped before their answers → revisit in step 8.
- Text printed along a circle comes out as letter fragments (one badge in the flyer).
- Our own glossary matching must cope with "Echtholz fronten" (a space where a soft hyphen was) → step 7.

### Step 3 – Upload + project ⬜ (next)

Upload a PDF → project created automatically → original file stored → segments stored in
the database → language detected **per segment** → source language confirmed or changed by hand.
Segments not in the source language are marked (they will not be translated).
Includes an end-to-end check of all sample PDFs: upload → database contents vs. the page images.

| Sub-part | Content | Status |
|---|---|---|
| 3a | Data model: Project, Document, Page, Segment tables + Alembic migrations | ⬜ |
| 3b | Language detection: `lingua-py` integration to detect language per segment | ⬜ |
| 3c | Upload API: `POST /api/projects` (accepts PDF, saves to disk, parses, detects languages, saves to DB) | ✅ |
| 3d | Project API: `GET /api/projects/{id}` and `PATCH /api/projects/{id}` (confirm source language) | ✅ |
| 3e | E2E tests: Upload sample PDFs and verify database contents | ✅ |
| 3f | Frontend UI: File dropzone, project setup view, confirm source language | ⬜ |

### Steps 4–11 ⬜
- **4 – Providers:** one interface; DeepL, Claude and a mock provider (used in CI). Shared contract tests.
- **5 – Glossary enforcement:** the experiment showed DeepL translates product/colour/brand
  names ("Class VI Black" → "Klasse VI Schwarz") and ignores Rotpunkt terms
  (Korpus → "body" instead of "carcase").
- **6 – Translation job:** background job with queued → running → done/failed, batching,
  partial failures.
- **7 – Highlighting:** F1/F2 deterministic (glossary, protected names), then F3–F5 via an
  LLM annotation pass that works for any provider.
- **8 – Preview:** side by side; fix form/table reading order here.
- **9 – Re-translate one segment.**
- **10 – QA:** untranslated segments, glossary terms not used.
- **11 – Playwright:** upload → translate → preview → re-translate → QA.

---

## Part 2 – Full feature set ⬜

Everything from the specification that Part 1 does not cover. Proposed order: first the
features that complete the core workflow (users → editing → approval → export), then the rest.

| # | Area | Features |
|---|---|---|
| 1 | **Users & roles** | M1 login, M2 roles (translator, reviewer, admin), M3 user management |
| 2 | **Manual editing** | G1 edit text, G2 replace terms, G3 add term to glossary from the editor, G4 comments |
| 3 | **Approval** | J1 "approve translation" locks it and produces the final version |
| 4 | **Export** | K1 Word, K2 Excel, K3 PDF, K4 Excel column mapping, K5 export templates, K6 export modes (translation only, original + translation, QA report, comments) |
| 5 | **More input formats** | B1 DOCX, B2 XLSX, B4 InDesign (IDML) |
| 6 | **Languages** | C3 several target languages at once |
| 7 | **Term details** | F6 term popover (translation used, alternatives, description), F7 inline term edit |
| 8 | **Glossary extensions** | H4 synonyms, H5 Excel import, H6 Excel export, H7 full duplicate check, H8 versioning, H9 approval status |
| 9 | **QA extensions** | I3 inconsistent translations, I4 unknown terms, I5 formatting problems |
| 10 | **Project management** | A4 archive, A5 reopen, A6 copy, A7 search & filter, A8 customer field |
| 11 | **History & search** | L1 project history, L2 search by project, file, customer, language, term, editor, period |
| 12 | **Dashboard** | N1 project overview, N2 most-used glossary terms, N3 statistics |
| 13 | **Settings** | O1 defaults, O2 highlight colours, O3 AI model and API keys |
| 14 | **Platform** | P2 multi-user concurrency, P3 responsive UI |
| 15 | **Phase-2 items from the specification** | Translation memory, PowerPoint/XML/CSV, multilingual glossary approval workflow, automatic detection of new terms, version comparison, role-based approvals with notifications, analytics |

---

## Part 3 – Scale ⬜

Measure first, then fix the real bottlenecks.

| Area | Planned work |
|---|---|
| **Measure** | Load tests (k6 or Locust); profiling of parser and translation jobs on large PDFs (100+ pages) |
| **Jobs** | Move translation jobs from in-process to a queue (Redis + arq or Celery); retries, rate limits per provider |
| **Storage** | Original files and exports in object storage (S3 / MinIO) behind the existing storage interface |
| **Database** | Trigram index for glossary search (`ILIKE`), connection pooling, query review |
| **Cost** | Translation memory/cache so repeated segments are not sent to DeepL/LLM again; batching |
| **Frontend** | Code splitting (bundle is > 500 kB), list virtualization for large documents |
| **Operations** | Structured logging, metrics, tracing; stateless API for horizontal scaling; deployment pipeline |
| **Security** | Upload limits, file validation, secrets handling, dependency scanning |

---

## Decision log

| Date | Decision |
|---|---|
| 2026-10-03 | Three parts: MVP → full feature set → scale |
| 2026-10-03 | Stack: FastAPI + React/TypeScript; DeepL as the second provider |
| 2026-10-03 | Part 1 ingests PDF only; DOCX/XLSX move to Part 2 |
| 2026-10-03 | Glossary: one entry per concept, 7 languages, category + description |
| 2026-10-03 | PyMuPDF despite AGPL; headers and footers are translated too |
| 2026-10-04 | No heuristic text clean-up; let DeepL handle hyphenation (confirmed by experiment) |
| 2026-10-04 | Bold-heading rule removed: on the samples it mostly produced wrong headings |
| 2026-10-04 | One source language → one target language; other languages are left untranslated |
| 2026-10-04 | Form/table reading order deferred to the preview step |
