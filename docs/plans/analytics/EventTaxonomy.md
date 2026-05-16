# Event Taxonomy

Also see:

- [Analytics.md](Analytics.md)
- [AnalyticsArchitecture.md](AnalyticsArchitecture.md)
- [AnalyticsVendors.md](AnalyticsVendors.md)
- [PublicDashboardIdeas.md](PublicDashboardIdeas.md)

This was AI-generated and has NOT yet been reviewed by a human. It's probably wrong.

## Philosophy

Events should be:

- intentional
- human-readable
- minimally invasive
- useful for concrete product questions

Avoid collecting events “just in case.”

## Naming Conventions

Preferred format:

```text
noun_verb
```

Examples:

- edit_started
- edit_saved
- search_performed
- photo_uploaded

Avoid:

- vague names
- vendor-specific naming
- internal implementation details

## Core Event Categories

### Discovery Events

#### search_performed

Properties:

- query_length
- results_count
- logged_in

Purpose:

- improve search quality
- identify missing content

#### search_zero_results

Properties:

- normalized_query
- logged_in

Purpose:

- identify preservation/documentation gaps

#### machine_page_viewed

Properties:

- machine_id
- manufacturer
- era
- has_media

Purpose:

- understand discovery patterns

### Contribution Events

#### edit_started

Properties:

- page_type
- logged_in

Purpose:

- measure contribution funnel entry

#### edit_saved

Properties:

- page_type
- duration_seconds
- is_first_edit

Purpose:

- understand successful contribution flows

#### edit_abandoned

Properties:

- page_type
- duration_seconds

Purpose:

- identify workflow friction

#### photo_uploaded

Properties:

- machine_id
- image_type
- upload_size_bucket

Purpose:

- understand preservation activity

### Community Events

#### account_registered

Properties:

- referral_source
- invite_source

Purpose:

- understand onboarding paths

#### moderation_action

Properties:

- action_type
- content_type

Purpose:

- monitor moderation workload

## Public Interest Metrics

The following aggregate metrics may eventually be public:

- searches needing articles
- contribution growth
- preservation coverage
- active contributors
- media upload trends
- documentation completeness
- machine coverage by era/manufacturer

## Explicit Non-Goals

We intentionally avoid:

- behavioral fingerprinting
- advertising profiles
- engagement addiction metrics
- cross-site tracking
- predictive behavioral scoring
- manipulative retention analytics
