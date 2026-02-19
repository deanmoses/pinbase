# Deployment on Railway

Pinbase runs as a **single [Railway](https://railway.com/) service**: one Docker container running Django/Gunicorn that serves both the API and the static SvelteKit frontend.
No Node.js runs in production.

## Architecture

```text
Browser ──→ Railway (single Gunicorn service)
              │
              ├─ /_app/*, static assets  → WhiteNoise (physical files)
              ├─ /api/*                  → Django Ninja API
              ├─ /admin/*               → Django Admin
              ├─ /about (prerendered)   → catch-all → about.html
              └─ /dashboard (CSR)       → catch-all → index.html (SPA shell)
```

### How it works

1. **Docker multi-stage build**: Stage 1 builds the SvelteKit frontend with
   Node/pnpm. Stage 2 copies the static output into the Python image. No
   Node.js runs at runtime.

2. **WhiteNoise `WHITENOISE_ROOT`**: Points to the frontend build directory.
   WhiteNoise serves any request that matches a physical file (JS bundles,
   CSS, images) directly from the middleware layer, before Django URL routing.

3. **Django catch-all view**: For routes that don't match a physical file
   or `/api/`/`/admin/`, Django tries prerendered HTML (`path.html`, then
   `path/index.html`), then falls back to `index.html` — the SvelteKit SPA
   shell. The client-side router handles navigation from there.

4. **Migrations on deploy**: Railway's `preDeployCommand` runs
   `manage.py migrate` before the new container accepts traffic. If the
   migration fails, the old container keeps serving.

### Request flow examples

| Request                       | Handled by                               |
| ----------------------------- | ---------------------------------------- |
| `GET /api/models/`            | Django Ninja                             |
| `GET /admin/`                 | Django Admin                             |
| `GET /_app/immutable/app.js`  | WhiteNoise (physical file)               |
| `GET /manufacturers/williams` | Catch-all → `index.html` → SvelteKit SPA |
| `GET /`                       | Catch-all → `index.html` → SvelteKit SPA |

## Setup

### 1. Create Railway project

In your Railway workspace, create a new project and connect the GitHub repo.
Railway auto-detects the `Dockerfile` via `railway.toml`.

Add a **Postgres** plugin to the project. Railway sets `DATABASE_URL`
automatically via a reference variable.

### 2. Set environment variables

In the Railway service dashboard:

| Variable               | Value                                                                         |
| ---------------------- | ----------------------------------------------------------------------------- |
| `SECRET_KEY`           | Random string: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG`                | `false`                                                                       |
| `ALLOWED_HOSTS`        | Your Railway domain, e.g. `pinbase-production.up.railway.app`                 |
| `CSRF_TRUSTED_ORIGINS` | Full origin, e.g. `https://pinbase-production.up.railway.app`                 |

`DATABASE_URL` and `PORT` are set automatically by Railway.

### 3. Deploy

Push to `main`. Railway builds the Docker image and deploys. The
`preDeployCommand` in `railway.toml` runs migrations before the new
container starts accepting traffic.

### 4. Create superuser (one-time)

In the Railway service shell (or via `railway run`):

```bash
uv run python manage.py createsuperuser
```

## Custom domain

1. Add a custom domain in Railway project settings
2. Update `ALLOWED_HOSTS` to include the domain
3. Update `CSRF_TRUSTED_ORIGINS` to include `https://yourdomain.com`

## Troubleshooting

**Health check fails after deploy**:
The health check hits `/api/health`. Check the deploy logs for Python
errors. Common causes: missing `SECRET_KEY`, database connection issues,
or a bad migration.

**"Frontend build directory not found" error**:
The Docker build's Node stage failed to produce `frontend/build/`. Check
the build logs for pnpm/SvelteKit errors. In production (`DEBUG=false`),
Django fails fast if the frontend build is missing.

**Bad migration**:
`preDeployCommand` runs migrations before swapping containers. If a
migration fails, the old container keeps serving and the deploy is marked
as failed. Fix the migration and push again. Railway does not automatically
roll back the database — if a migration partially applied, you may need to
manually fix it via `railway run`.
