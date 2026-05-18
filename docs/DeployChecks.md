# Deployment Preflight Checks

This documents how to build pre-flight deployment checks. These checks run once at deploy time, in-process, before the new container takes traffic.

It uses preDeploy refusal gate, implemented via Django's system check framework.

## We automate aggressively

These checks are important; we automate agressively. See [DeployAutomation.md](DeployAutomation.md).

## We also have build-phase checks

Before this deploy phase, while building the build, we also gate aggressively. See [BuildChecks.md](BuildChecks.md).

## How to use these checks when managing the service

For the operator-facing view (what `preDeployCommand` does, how failures surface in Railway), see [Hosting.md](Hosting.md).

## Scoping conventions

### One service, one env

Backend and frontend ship in the same Railway container, with the same env-var scope. Anything Railway sets on the service is visible to both Django at runtime and SvelteKit at build + runtime. There is no per-process env separation to work around.

### Frontend checks belong in Python

Because backend and frontend share an env, every env var the frontend needs is readable from `os.environ` in Django. There is no separate frontend preflight.

When a new `PUBLIC_*` var becomes required in production, the assertion goes in `apps/<name>/checks.py`, not in `vite.config.ts`, `instrumentation.server.ts`, or `hooks.client.ts`.

### Error vs Warning

- **Error** — the deploy is broken without this. Block promotion. Examples: missing `SENTRY_DSN` in production, misconfigured storage credentials.
- **Warning** — operator should notice, but the service still works. Surface in logs without blocking. Example: `core.W001` (`RATE_LIMIT_TRUST_PROXY_HEADERS` off in non-DEBUG — IP rate limiters degrade silently but the site still runs).

Default to Error per [DeployAutomation.md](DeployAutomation.md). Warnings exist only for cases where the site genuinely still works and a human will see the message soon (we have no such humans for unattended deploys — use Warning sparingly).

### Assert env-var shape, don't probe services

Deploy checks run in-process during `preDeployCommand`. They can read `settings` and `os.environ` cheaply, but they are the wrong place to open sockets, hit S3/R2, or query the DB. Network probes are slow, flaky, and turn a deploy gate into a dependency-availability gate — a transient blip in an upstream service blocks promotion of an unrelated change.

Assert that env vars are **present and well-formed** (correct prefix, parseable URL, expected length). "Can we actually reach the bucket" is a runtime-readiness concern, not a deploy-gate concern.

## Adding a check

Checks live in `apps/<name>/checks.py` and are imported from the app's `AppConfig.ready()`. Two decorator shapes:

```python
from collections.abc import Sequence
from typing import Any

from django.apps.config import AppConfig
from django.core.checks import CheckMessage, Error, Tags, Warning, register

# Always runs (under `manage.py check` and at server boot).
@register(Tags.models)
def check_something(
    app_configs: Sequence[AppConfig] | None,
    **kwargs: Any,  # noqa: ANN401
) -> list[CheckMessage]:
    _ = app_configs, kwargs
    ...

# Only runs under `manage.py check --deploy` — i.e., in production preflight.
@register(Tags.security, deploy=True)
def check_prod_env(
    app_configs: Sequence[AppConfig] | None,
    **kwargs: Any,  # noqa: ANN401
) -> list[CheckMessage]:
    _ = app_configs, kwargs
    ...
```

`**kwargs: Any` is required by Django's check-framework signature (it may carry forward-compatible options like `databases`); the `noqa: ANN401` is the documented escape hatch. The `_ = app_configs, kwargs` line marks them as intentionally unread.

Pick a tag from `django.core.checks.Tags` that matches the domain (`security`, `models`, `database`, etc.). Return a list of `Error` / `Warning` with a stable `id` like `core.E101` or `core.W001` — the id is what operators grep for in logs.

See [`apps/core/checks.py`](../backend/apps/core/checks.py) for the full shape and `check_rate_limit_proxy_trust` as a worked deploy-gated example.

### Running deploy checks locally

`--deploy` checks are skipped under `DEBUG=True`, so reproducing what Railway runs requires faking a production-shaped env:

```sh
DEBUG=false \
RATE_LIMIT_TRUST_PROXY_HEADERS=false \
SECRET_KEY=dummy123456789012345678901234567890123456789012345 \
  uv run python manage.py check --deploy
```

Flip the var your check inspects to confirm it actually fires; flip it back to confirm it goes quiet.

### Testing

Every deploy-gated check should have a unit test that sets the relevant `settings`/env state and asserts the check returns (or doesn't return) the expected message id. The id is the contract — operators search logs for `core.W001`, not for the human-readable message — so pin it in the test.
