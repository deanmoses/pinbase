# Pinball Database

An interactive database of pinball machines.

## Architecture

Django + SvelteKit monorepo. Django owns the data model, APIs, and admin UI. SvelteKit handles the user-facing frontend.

- **Backend**: Django + Django Ninja API at `/api/`, admin at `/admin/`
- **Frontend**: SvelteKit with static adapter (CSR for authenticated pages, prerendered for public)
- **Auth**: Session-based, same-origin (no JWT, no CORS)
- **Dev proxy**: SvelteKit proxies `/api/` and `/admin/` to Django — single origin in dev and prod

## Quickstart

**Requirements**: Python 3.14+, Node 24+, [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) (or enable via `corepack enable`)

```bash
cp .env.example .env
make bootstrap
make dev
```

Then open http://localhost:5173

To create a Django admin superuser:

```bash
cd backend && uv run python manage.py createsuperuser
```

## Commands

| Command           | What it does                                               |
| ----------------- | ---------------------------------------------------------- |
| `make bootstrap`  | Install all deps, run migrations, generate API types       |
| `make dev`        | Start Django + SvelteKit dev servers                       |
| `make test`       | Run backend (pytest) + frontend (vitest) tests             |
| `make lint`       | Run ruff (backend) + eslint/prettier (frontend)            |
| `make quality`    | Lint + type check (svelte-check)                           |
| `make api-gen`    | Export OpenAPI schema and regenerate TypeScript types      |
| `make agent-docs` | Regenerate CLAUDE.md and AGENTS.md from docs/AGENTS.src.md |

## Project Structure

```text
backend/          Django project (uv, pyproject.toml)
frontend/         SvelteKit project (pnpm, package.json)
scripts/          POSIX shell scripts for bootstrap, dev, test, lint
docs/             Agent documentation source
Makefile          Thin wrappers around scripts/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the PR workflow.

## AI Agent Docs

`CLAUDE.md` and `AGENTS.md` are **generated** from `docs/AGENTS.src.md`. Never edit them directly — edit the source and run `make agent-docs`.
