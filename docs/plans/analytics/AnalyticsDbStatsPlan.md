# Analytics DB-Stats Plan

This doc covers DB-derived stats for [AnalyticsPlan.md](AnalyticsPlan.md). The questions it answers come from [AnalyticsQuestions.md](AnalyticsQuestions.md).

Whereas the other plans use PostHog to instrument visitor and contributor _behavior_, this plan derives counts and trends directly from the production database — `User`, `ChangeSet`, `Media`, and friends. It's the source of truth for anything about "what's in the system right now": signups, edits, contributors active in a period, retention cohorts, the 80/20 editor curve.

## Admin dashboard answers some of this

The [admin dashboard](AdminDashboard.md) ships the windowed-counts slice of this plan: signups, user-attributed edits, and successful uploads over rolling 24h / 7d / total windows, each with a `last_at` timestamp. It does not cover first-edit conversion, repeat contributors, monthly distinct-editor counts, retention cohorts, period-over-period deltas, or the 80/20 curve — those remain open below.

## What Questions It Answers

| Question                                                                               | What data answers it                                                                     |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Signups completed in a period                                                          | Count of `User` rows by `date_joined`                                                    |
| New accounts that made a first edit, and how long after signup                         | `User.date_joined` joined to that user's earliest `ChangeSet.created_at`                 |
| Media uploads completed in a period                                                    | Count of `Media` rows by `created_at` (only completed uploads persist)                   |
| Repeat contributors: second edit within 30 days of first                               | `ChangeSet` grouped by user, comparing earliest and second-earliest timestamps           |
| Contributors active in a given month                                                   | Distinct `ChangeSet.user_id` where `created_at` falls in the month                       |
| Retention cohorts: of week-N new contributors, how many still active 3 months later    | `User.date_joined` cohorted by week, joined to `ChangeSet` activity in each later window |
| Period-over-period edit counts (week-vs-week, month-vs-month, eventually year-vs-year) | Count of `ChangeSet` rows grouped by period                                              |
| Period-over-period active-contributor counts                                           | Distinct `ChangeSet.user_id` grouped by period                                           |
| 80/20 editor-distribution curve                                                        | `ChangeSet` grouped by user, counted, ranked                                             |

## Implementation: TBD

Could be fancy with charts, could be simple with a SQL statement.
