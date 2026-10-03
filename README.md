# Rotpunkt Translate

AI-assisted translation tool for kitchen-industry documents. It translates documents while respecting company glossaries, kitchen terminology and protected product names, and
highlights terms so a reviewer can see what the AI did and why.

> Work in progress. Part 1 (MVP) is being built step by step; see the roadmap below.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Translation | Claude (LLM) and DeepL behind a common provider interface |
| Testing | pytest, Vitest + Testing Library, Playwright |
| Tooling | uv, ruff, mypy (strict), ESLint, Docker Compose, GitHub Actions |

## Quick start

```bash
docker compose up --build
```

- App: http://localhost:5173
- API docs: http://localhost:8000/docs

## Local development

Requirements: [uv](https://docs.astral.sh/uv/), Node.js ≥ 22.12, Docker (for Postgres).

```bash
docker compose up -d db

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
uv run pytest

cd frontend
npm install
npm run dev
npm test
```

## Repository layout

```
backend/    FastAPI app (api, models, schemas, parsers, providers, services) + tests
frontend/   React app (pages, components, api client) + tests
e2e/        Playwright end-to-end tests
samples/    Links to public reference documents and seed terminology
```

## Roadmap

**Part 1 – MVP:** upload PDF → detect language → translate with glossary enforcement →
side-by-side preview with term highlighting → re-translate segments → quality checks.

**Part 2 – Full feature set:** DOCX/XLSX support, export, manual editing, approval workflow, users and roles,
dashboard, history, search, glossary import/export and versioning.

**Part 3 – Scale:** job queue, object storage, profiling and load testing.
