# Ingestion Refactor Plan

## Context

Pinbase currently ingests data from multiple external sources, primarily OPDB
and IPDB, then translates those source records into Pinbase's claims-based
catalog model.

The current fragility is not mainly a scale problem. The dataset is modest. The
hard parts are:

- translating between different source worldviews, especially OPDB's
  play-equivalence / alias structure and Pinbase's richer relationship model
- keeping parsing, matching, and relationship logic understandable
- avoiding duplicated normalization logic across Python and DuckDB
- making heuristics and overrides auditable rather than implicit

DuckDB in `data/explore` remains useful for ad hoc exploration of raw source
files, but it is not intended to be a second implementation of Pinbase's
normalization semantics.

## Goals

- Keep the core normalization and ingest logic in Python.
- Refactor incrementally rather than rewrite the whole ingestion stack.
- Make relationship derivation explicit, testable, and easier to debug.
- Preserve the claims/provenance architecture as the canonical persistence
  layer.
- Reduce hidden side effects and "patch-on-patch" control flow in ingest
  commands.
- Turn ambiguous heuristic decisions into visible review output where
  appropriate.

## Non-Goals

- Replacing Django or the claims system
- Moving core logic into SQL
- Making DuckDB part of the canonical ingest pipeline
- Introducing workflow orchestration tools like Airflow, Prefect, or Dagster
- Prioritizing incremental ingest over correctness and maintainability

## Core Principles

### 1. Python is the canonical normalization layer

All source translation, identity matching, and relationship classification
should live in Python. DuckDB may still be used to inspect raw OPDB/IPDB dumps,
but it should not duplicate business logic that Django relies on.

### 2. Separate normalization from persistence

The code should first produce explicit intermediate records and review issues,
then persist claims in a later step. The code that decides "what is true" should
not be tightly coupled to the code that writes database rows.

### 3. Prefer explicit intermediate records over mutable dict side effects

Temporary fields like `_variant_of_slug` or special-case mutations of lookup
dicts make the pipeline hard to reason about. Intermediate records should make
state transitions visible and inspectable.

### 4. Heuristics should propose, not quietly canonize

If a source structure is ambiguous, the pipeline should produce either:

- a high-confidence automatic decision with a named rule
- or a review issue that calls out the ambiguity

### 5. Declarative mappings belong in data files

Shared lookup tables and editorial mappings should move toward structured data
files instead of being scattered across management commands and SQL.

## Recommended Technical Direction

Use plain Python plus typed data structures.

- Use `dataclasses` or `TypedDict` for raw and normalized record shapes.
- Add explicit validation helpers at source boundaries rather than relying on
  ad hoc `dict.get()` checks throughout the pipeline.
- Keep Django management commands as entrypoints.
- Keep DuckDB limited to exploratory raw-data analysis.

`pydantic` and `polars` are not part of the core recommendation for this
refactor.

- `pydantic` could be reconsidered later if richer validation and error
  reporting become worth the extra dependency.
- `polars` is not a good fit for the hardest parts of the current problem,
  which are relationship- and graph-shaped rather than bulk table operations.

## Target Architecture

The goal is not to create a large framework, but to split the current ingest
commands into clearer Python passes.

Suggested modules:

- `backend/apps/catalog/ingestion/schemas.py`
  - typed raw and normalized record definitions
- `backend/apps/catalog/ingestion/validators.py`
  - source-shape and required-key checks
- `backend/apps/catalog/ingestion/identity.py`
  - cross-source identity matching helpers
- `backend/apps/catalog/ingestion/opdb_normalize.py`
  - OPDB-specific parsing and normalization
- `backend/apps/catalog/ingestion/opdb_relationships.py`
  - alias promotion, clone/variant classification, and review issue generation
- `backend/apps/catalog/ingestion/persist.py`
  - conversion of normalized decisions into claims / model updates

This is a target shape, not a mandate to create all files immediately.

## Explicit Intermediate Records

The pipeline should operate on explicit record types such as:

- `RawOpdbMachineRecord`
- `RawIpdbMachineRecord`
- `NormalizedExternalMachine`
- `IdentityMatch`
- `RelationshipCandidate`
- `ReviewIssue`

Important fields to capture explicitly:

- source identity (`source_name`, `opdb_id`, `ipdb_id`, group IDs, alias IDs)
- normalized manufacturer identity
- relationship candidate type (`variant`, `clone`, `conversion`, `title_link`)
- rule used to derive the candidate
- confidence level or review requirement
- human-readable explanation for debugging

## Review Output

The normalization layer should be able to emit structured review issues for
cases like:

- non-physical OPDB groups with multiple plausible canonical aliases
- alias-parent relationships that depend on weak heuristics
- manufacturer mismatches that may be clones or may be bad source data
- title assignments suppressed by `split_from_opdb_group`
- source records with missing keys or unexpected structure

These review issues do not need a new UI immediately. A JSON or Markdown report
produced during ingest is sufficient for the first phase.

## Validation Strategy

Validation already exists in `validate_catalog.py` and `data/explore/04_checks.sql`.
This refactor should strengthen validation rather than replace it.

Add checks in two places:

### Input validation

Before source-specific normalization begins:

- required top-level keys exist
- known record-type flags are present where expected
- important nested objects have required fields

### Output validation

After normalization and/or persistence:

- no orphaned relationship targets
- no self-referential or chained `variant_of`
- no unresolved FK claim values for authoritative source outputs
- summary counts for auto-created taxonomy / low-confidence mappings
- diff-oriented reporting when ingest behavior changes materially

## Declarative Mapping Work

Move shared mappings into structured files in `data/` where feasible.

Candidates include:

- manufacturer aliases and resolution hints
- IPDB theme/tag mapping tables
- credit-role normalization tables
- OPDB alias-promotion override rules

The short-term goal is not total elimination of code-driven rules. It is to
reduce duplication and make the editorially maintained parts obvious.

## DuckDB Guidance

DuckDB remains allowed for exploration of raw third-party files.

It should not:

- re-implement canonical manufacturer resolution
- derive Pinbase relationship semantics independently
- act as a second source of truth for normalized catalog logic

If exploratory SQL becomes useful enough to preserve long-term, keep it focused
on source inspection and data auditing, not catalog derivation.

## Phased Execution Plan

### Phase 1: OPDB Alias / Non-Physical Refactor

Scope only the most fragile part of the pipeline.

Work:

- extract alias and non-physical handling out of `ingest_opdb.py`
- replace temporary dict mutation with explicit intermediate records
- make promotion / clone / variant rules named and testable
- emit review issues for ambiguous cases
- keep existing DB outputs and tests green

Success criteria:

- `ingest_opdb.py` becomes materially shorter and easier to read
- alias behavior is covered by focused tests on the extracted module
- no equivalent logic remains in DuckDB that must be kept in sync

### Phase 2: Source Validation and Shared Mappings

Work:

- add boundary validation for OPDB and IPDB dumps
- extract scattered lookup tables into structured data files where appropriate
- standardize warning and review reporting

Success criteria:

- unexpected source shape changes fail early with useful messages
- shared mappings are no longer duplicated across Python and SQL

### Phase 3: IPDB Normalization Cleanup

Work:

- isolate manufacturer parsing and resolution into clearer passes
- make theme / credit parsing behavior more explicit
- distinguish authoritative mappings from best-effort fallbacks

Success criteria:

- IPDB normalization logic is easier to test independently of persistence
- auto-created or weakly inferred values are clearly reported

### Phase 4: Persistence Boundary Cleanup

Work:

- make claim-writing steps consume normalized records rather than raw dicts
- keep persistence helpers thin and source-agnostic where possible
- document the boundary between normalization decisions and claim assertion

Success criteria:

- the write path is mostly boring
- domain complexity is isolated to normalization modules

## Risks and Tradeoffs

- Refactoring around explicit intermediate records may feel slower at first
  because it moves hidden assumptions into code that must be named.
- Some current heuristics may turn out to be too ambiguous to preserve as
  fully automatic behavior.
- Splitting logic into modules can become over-engineering if done all at once.
  The work should proceed only when each extraction makes a real hotspot simpler.

## Immediate First Step

Start with the OPDB alias / non-physical path in
`backend/apps/catalog/management/commands/ingest_opdb.py`.

Do not begin with a repo-wide framework change.

The first refactor should:

- extract the alias classification logic into a dedicated Python module
- introduce typed intermediate records for that slice only
- preserve current outputs
- add tests that lock down the extracted behavior before broader cleanup

If this slice becomes easier to understand and maintain, use the same pattern
for the rest of the ingest pipeline.
