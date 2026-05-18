# Deploy Automation

The design philosophy behind the project's deployment safeguards.

## Why automation matters

Flipcommons is run by a [small team of volunteers](SmallTeam.md). There's no professional IT, no one monitoring deploys, no one reviewing build logs after every merge to `main`. Deploys happen automatically. Any signal that requires a human to notice will get missed.

## Refuse, don't warn

When something the deploy depends on isn't working, the gate should fail loudly and keep the old version serving. A `console.warn`, a degraded mode, a "we'll check the logs later" — all of these are how broken state ships to production unnoticed.

Cost is asymmetric. A false positive (gate fires when nothing's broken) keeps the old version serving. A false negative (gate passes when something's broken) ships a degraded site that nobody notices, potentially for days or weeks. When in doubt, refuse.

## Refuse to promote, no rollback

Railway does not _revert_ a live deploy on failure — it refuses to _promote_ the new one. The old container keeps serving. This makes aggressive gating safe: a too-eager check costs minutes of investigation, not minutes of downtime.

## Two refusal phases

Each deploy has two gating points:

| Phase     | When                                                 | What's gated                                                    | Implementation                     |
| --------- | ---------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------- |
| Build     | `pnpm build` and other `RUN` steps in the Dockerfile | Build artifacts, sourcemap upload, build-time secrets           | [BuildChecks.md](BuildChecks.md)   |
| preDeploy | `railway.toml`'s `preDeployCommand`                  | Runtime env vars, database schema, in-process runtime contracts | [DeployChecks.md](DeployChecks.md) |

Build refusals run earlier and catch artifact-level issues (a broken bundle, a missing sourcemap). preDeploy refusals run later and catch environment-level issues (a missing env var, an incompatible migration).
