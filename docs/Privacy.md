# Privacy Principles

This is the internal principles doc. The user-facing privacy policy that implements these principles lives at [frontend/src/routes/(legal)/privacy/+page.svelte](<../frontend/src/routes/(legal)/privacy/+page.svelte>) (served at `/privacy`).

## Core Philosophy

We exist to preserve and share knowledge about pinball history and culture.

User trust is more important than maximizing data collection.

Analytics and operational data collection must always support:

- stewardship
- usability
- preservation
- reliability
- community health

not extraction or manipulation.

## Principles

### Data Minimization

Collect the smallest amount of data necessary to answer legitimate product and operational questions.

Avoid speculative collection.

### Minimal Public Disclosure

Display the minimum amount of personal information needed for community participation.

Users participate under a chosen username. Real names and other PII are NEVER to be shown publicly without explicit approval by the user. It should go without saying, but email addresses will NEVER be made public.

### No Advertising Ecosystem Participation

We will not:

- sell user data
- participate in behavioral advertising
- share analytics with ad networks
- perform cross-site tracking

### Explicit Instrumentation

Prefer explicit event instrumentation over blanket autocapture.

Preferred:

- intentional workflow events
- aggregate metrics
- scoped diagnostics

Avoid:

- indiscriminate collection
- keystroke capture
- excessive replay systems

### Respectful Session Replay

If session replay is used:

- it must be scoped and limited
- sensitive fields must be masked
- replay must support debugging and usability improvements only

Session replay must never become generalized behavioral surveillance.

### Public Interest Orientation

Analytics must reinforce Flipcommons as:

- a public knowledge resource
- a preservation project
- an enthusiast commons
- an open-web project

rather than a growth-optimization platform.

## Things Flipcommons Intentionally Avoids

- engagement addiction metrics
- manipulative notification funnels
- infinite-scroll optimization
- dark-pattern retention systems
- behavioral profiling
- fingerprinting
- shadow profiles
- ad-tech integrations
