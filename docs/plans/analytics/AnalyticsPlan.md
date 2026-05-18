# Analytics Rollout Plan

Also see:

- [Analytics.md](Analytics.md)
- [AnalyticsQuestions.md](AnalyticsQuestions.md) - what are we trying to answer with analytics
- [AnalyticsArchitecture.md](AnalyticsArchitecture.md)

## Tracks

Tracks are independent and ship as appetite allows.

- ✅ DONE: **[AnalyticsUntypedEventsPlan.md](AnalyticsUntypedEventsPlan.md)** — SDK skeleton + pageview firehose from the browser. Privacy lockdown lives here.
- **[AnalyticsTypedEventsPlan.md](AnalyticsTypedEventsPlan.md)** — typed, named events for questions the firehose can't answer.
- **[AnalyticsDbStatsPlan.md](AnalyticsDbStatsPlan.md)** — SQL against the production database for "what's in the system right now" stats (signups, edits, retention, the 80/20 editor curve). No analytics vendor involvement.

## Which track answers which question

The high-level questions from [AnalyticsQuestions.md § Root questions](AnalyticsQuestions.md#root-questions), mapped to the track that answers them.

| High-level question                                                | Track that answers it                                                                                                   |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Are we growing?                                                    | [Untyped Events](AnalyticsUntypedEventsPlan.md) for traffic; [DB Stats](AnalyticsDbStatsPlan.md) for signups + edits    |
| What's driving growth? — external sources                          | [Untyped Events](AnalyticsUntypedEventsPlan.md) (referrer breakdown)                                                    |
| What's driving growth? — our content                               | [Untyped Events](AnalyticsUntypedEventsPlan.md) (per-URL pageview counts)                                               |
| Theses borne out? — browsing-as-discovery                          | [Untyped Events](AnalyticsUntypedEventsPlan.md) (session pageview depth, free from the firehose)                        |
| Right features? — page-level usage                                 | [Untyped Events](AnalyticsUntypedEventsPlan.md)                                                                         |
| Theses borne out? — title-vs-model market                          | [Typed Events](AnalyticsTypedEventsPlan.md) (search-click target)                                                       |
| Right features? — in-page usage (claim revert, edit history, etc.) | [Typed Events](AnalyticsTypedEventsPlan.md) (generic `feature_used`)                                                    |
| Right features? — missing the mark / drop-off                      | [Typed Events](AnalyticsTypedEventsPlan.md) for flow-starts; [DB Stats](AnalyticsDbStatsPlan.md) for flow-completions   |
| Editor community healthy / engaged / growing?                      | [DB Stats](AnalyticsDbStatsPlan.md) (active contributors, retention, 80/20 curve)                                       |
| Theses borne out? — personas                                       | Not telemetry-answerable; user research                                                                                 |
| Right features? — missing features                                 | Mostly user research; zero-result on-site searches via [Typed Events](AnalyticsTypedEventsPlan.md) hint at catalog gaps |
