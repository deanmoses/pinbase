# Ingestion Refactor

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
normalization semantics. In practice, it has accreted its own parallel
implementation of much of this logic — manufacturer resolution, variant
derivation, type mappings — creating a second codebase that must stay in sync.

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
- Sharing a base class or generic framework between IPDB and OPDB ingest
  commands — each source has enough unique logic that a shared base class would
  create more abstraction than it removes duplication

## Core Principles

### 1. Python is the canonical normalization layer

All source translation, identity matching, and relationship classification
should live in Python. DuckDB may still be used to inspect raw OPDB/IPDB dumps,
but it should not duplicate business logic that Django relies on. As the Python
pipeline gains testable coverage of each transform, the corresponding DuckDB
SQL should be actively simplified — replaced with reads of Python-exported
intermediates rather than maintained as a parallel implementation.

### 2. Separate normalization from persistence

The code should first produce explicit intermediate records and review issues,
then persist claims in a later step. The code that decides "what is true" should
not be tightly coupled to the code that writes database rows.

### 3. Use explicit intermediate records for relationship derivation

Temporary fields like `_variant_of_slug` or special-case mutations of lookup
dicts make the pipeline hard to reason about. For relationship derivation and
identity matching — the hardest parts of the pipeline — intermediate records
should make state transitions visible and inspectable. Scalar field mapping
(name, year, player_count) does not need this treatment; the current
dict-to-claim pattern is adequate for simple fields.

### 4. Heuristics should propose, not quietly canonize

If a source structure is ambiguous, the pipeline should produce either:

- a high-confidence automatic decision with a named rule
- or a review issue that calls out the ambiguity

### 5. Prefer declarative mappings where appropriate

Large editorial lookup tables and shared mappings should move toward structured
data files rather than being scattered across management commands and SQL. Small
mapping dicts that are tightly coupled to parsing logic (e.g. type-code
mappings in `parsers.py`) are fine where they are.

## Recommended Technical Direction

Use plain Python plus typed data structures.

- Use `dataclasses` for raw and normalized record shapes.
- Add explicit validation helpers at source boundaries rather than relying on
  ad hoc `dict.get()` checks throughout the pipeline.
- Keep Django management commands as entrypoints.

`pydantic` and `polars` are not part of the core recommendation for this
refactor.

- `pydantic` could be reconsidered later if richer validation and error
  reporting become worth the extra dependency.
- `polars` is not a good fit for the hardest parts of the current problem,
  which are relationship- and graph-shaped rather than bulk table operations.

## Phased Execution Plan

### Phase 1: OPDB Relationship Extraction (with typed OPDB records)

Start with the known hotspot: OPDB alias, variant, and clone classification.
Introduce typed `OpdbRecord` as part of this extraction — not as a separate
broad pass across all sources.

**Typed OPDB records.** Create `backend/apps/catalog/ingestion/records.py`
with an `OpdbRecord` dataclass scoped to the fields needed for relationship
classification:

```python
@dataclass
class OpdbRecord:
    """Raw OPDB record — close to source shape, minimal normalization."""
    opdb_id: str
    name: str
    ipdb_id: int | None = None
    manufacturer_name: str = ""
    manufacture_date: str = ""
    physical_machine: int = 1
    is_machine: bool = True
    features: list[str] = field(default_factory=list)
    # ... remaining fields

    @classmethod
    def from_raw(cls, d: dict) -> "OpdbRecord":
        """Map raw JSON keys to Python field names. Key mapping only."""
        mfr = d.get("manufacturer") or {}
        return cls(
            opdb_id=d["opdb_id"],
            name=d.get("name", "Unknown"),
            manufacturer_name=mfr.get("name", ""),
            # ...
        )
```

The `from_raw()` factory does key mapping and minimal type coercion only.
`__post_init__` does validation (required fields, value ranges). Heavier
normalization — HTML unescape, manufacturer string parsing, date parsing —
stays in `parsers.py` functions, called explicitly as a separate step. The
record should be close to the source shape, not a normalized shape.

**Relationship extraction.** Create
`backend/apps/catalog/ingestion/opdb_relationships.py` to replace the current
pattern where `ingest_opdb.py` injects temporary fields (`_variant_of_slug`,
`_skip_opdb_id_claim`, `_title_slug`) into raw record dicts.

The extracted module operates on explicit intermediate records:

```python
@dataclass
class RelationshipCandidate:
    source_opdb_id: str
    target_opdb_id: str     # source-side identifier, not a slug
    relationship_type: str  # "variant", "clone", "conversion", "title_link"
    rule_name: str          # named rule that produced this decision
    confidence: str         # "auto" or "review"
    explanation: str        # human-readable reason

@dataclass
class ReviewIssue:
    source_opdb_id: str
    issue_type: str
    description: str
    context: dict           # relevant data for human review
```

Relationship candidates use source-side identifiers (`target_opdb_id`), not
slugs. Translation from OPDB IDs to Pinbase slugs belongs in the persist step,
where the model lookup dicts already exist. This keeps the extraction module
independent of DB state and makes the intermediate records reusable for export
and testing.

The normalization layer should emit review issues for cases like:

- non-physical OPDB groups where `_pick_default_alias()` makes a weak choice
- alias-parent relationships that depend on heuristic manufacturer comparison
- manufacturer mismatches that may be clones or may be bad source data
- title assignments suppressed by `split_from_opdb_group`

Review issues do not need a UI. A JSON or Markdown report produced during
ingest is sufficient.

Success criteria:

- `ingest_opdb.py` becomes materially shorter — no `_variant_of_slug` dict
  mutation
- Alias/variant/clone behavior is covered by focused unit tests on the
  extracted module — not just `validate_catalog`, but tests that exercise
  specific classification rules (clone detection, chain collapse, default alias
  selection) with small synthetic inputs so failures are local and diagnostic
- `validate_catalog` passes before and after

### Phase 2: Typed IPDB Records

Extend the typed record pattern to IPDB. Create `IpdbRecord` in the existing
`records.py`:

```python
@dataclass
class IpdbRecord:
    """Raw IPDB record — close to source shape, minimal normalization."""
    ipdb_id: int
    title: str
    manufacturer_id: int | None = None
    manufacturer: str = ""
    date_of_manufacture: str = ""
    mpu: str = ""
    type_short_name: str = ""
    type_full: str = ""
    players: int | None = None
    production_number: str = ""
    # ... remaining fields

    @classmethod
    def from_raw(cls, d: dict) -> "IpdbRecord":
        """Map raw JSON keys to Python field names. Key mapping only."""
        return cls(
            ipdb_id=d["IpdbId"],
            title=d["Title"],
            # ...
        )
```

Same discipline as `OpdbRecord`: `from_raw()` does key mapping and minimal
coercion. Heavier normalization (HTML unescape, manufacturer string parsing,
date extraction) stays in `parsers.py`, called explicitly after construction.

Success criteria:

- `ingest_ipdb.py` parses raw JSON into typed records before any DB work
- A renamed or removed upstream field produces a clear error, not a silent None
- Existing DB outputs unchanged; `validate_catalog` passes before and after

### Phase 3: Structured Error Reporting

Replace the catch-all `except Exception` blocks in both ingest commands with
specific error categories:

- **`ParseError`** — Source data doesn't match expected shape. Logged with
  source record ID and field name. Record is skipped, ingest continues.

- **`MatchError`** — Can't resolve a foreign reference (unknown MPU string,
  unresolvable manufacturer). Formalizes the existing `unknown_mpu_strings`
  collection pattern.

- **`DataConflict`** — Two sources assert incompatible values for the same
  field. Already handled by the claims system, but currently invisible during
  ingest. Surface these as warnings. Care needed to avoid noise: the claims
  system is designed for multi-source disagreement, so only surface conflicts
  that indicate likely data problems (e.g. manufacturer mismatch on the same
  machine), not routine priority-based overrides.

**Fail-fast on systemic drift.** Skip-and-continue is correct for isolated bad
records, but not for schema-level changes. If `ParseError` count exceeds a low
threshold (e.g. 5 records or 1% of the source file, whichever is larger), fail
the entire run immediately. "OPDB renamed a field" should abort the ingest, not
silently produce a partial import of hundreds of incomplete records.

Collect all errors per-run and emit a structured summary at the end, rather
than interleaving stack traces with progress output.

Success criteria:

- A bug in ingest code raises immediately rather than being caught and logged
- Bad source data is skipped with a clear, categorized message
- Systemic source drift aborts the run early rather than normalizing a broken
  import
- End-of-run summary shows counts by error category

### Phase 4: DuckDB Simplification

Shift DuckDB from reimplementing transforms to reading Python-produced
intermediates.

The Python pipeline gains the ability to export its intermediate results —
typed records from Phases 1–2, relationship candidates from Phase 1 — as files
that DuckDB can read. The export format (CSV, JSON, or Parquet) will be
decided when this phase begins, based on what the intermediates actually look
like and whether adding a dependency (e.g. `pyarrow`) is worthwhile.

Changes to DuckDB:

- `01_raw.sql` stays as-is — raw JSON reads for source inspection
- `02_staging.sql` progressively simplified: replace reimplemented transforms
  (manufacturer resolution, variant derivation, type mappings) with reads of
  Python-exported intermediates
- `04_checks.sql` kept as secondary validation alongside `validate_catalog`

The goal is that DuckDB becomes a querying layer over both raw source data and
Python-produced intermediates, with no duplicated transform logic.

**Artifact contract.** The exported intermediate files are internal debug
artifacts, not a public API, but they still need a lightweight contract to
avoid silent breakage. Document the exported files and their columns in
`data/explore/README.md` (or equivalent). If the Python export shape changes,
update the SQL that reads it in the same commit. Start with one concrete
example artifact (e.g. `data/intermediates/opdb_relationships.csv`) to
establish the pattern before expanding. This replaces SQL-duplication coupling
with a simpler, explicit coupling that's easy to maintain.

Success criteria:

- `02_staging.sql` no longer reimplements manufacturer resolution, variant
  derivation, or type mappings
- DuckDB queries over Python intermediates produce the same results as the
  old SQL-based transforms
- Ad hoc exploration workflows still work

### Phase 5: Dry-Run Mode

Add `--dry-run` to `ingest_all` and each sub-command.

**Initial scope (this phase):** Wrap the entire `handle()` in a transaction
that is rolled back at the end. `bulk_assert_claims` stats are captured and
reported but not committed. Output shows: N models would be created, N claims
would change, N persons would be created. This is coarse — it runs the full
pipeline and discards the result — but it gives the most-wanted feature: "will
this ingest blow things up?"

**After Phase 6 (parse/persist separation):** Dry-run becomes more precise.
The parse phase runs independently, the persist phase can be skipped entirely
or run in rollback mode, and the output can distinguish parse errors from
persistence errors. This is the long-term target, but it depends on a clean
write boundary.

Success criteria:

- `ingest_all --dry-run` completes without writing to the database
- Output reports what would change in sufficient detail to catch regressions

### Phase 6: Parse/Persist Separation

Only after Phases 1–5 are stable. This is what makes Phase 5's dry-run
precise and trustworthy.

Restructure each ingest command into two clear phases:

1. **Parse phase** — Read the raw file, produce a list of typed dataclass
   records. No database access. This is independently testable.

2. **Persist phase** — Take parsed records, match/create models, build
   claims, bulk-assert.

The management command's `handle()` becomes a thin orchestrator:

```python
def handle(self, *args, **options):
    records = IpdbRecord.load(options["ipdb"])  # parse phase
    self.persist(records)                        # persist phase
```

Success criteria:

- Parse phase can be tested with no database
- Persist phase receives only typed records, not raw dicts

### Phase 7: Shared Utilities

Only when duplication between IPDB and OPDB commands clearly warrants
abstraction. Not before.

Candidates:

- **`ManufacturerResolver`** — Encapsulates the entity-name → slug,
  trade-name → slug, and auto-create-on-miss logic that both commands
  implement independently.

- **`ClaimCollector`** — A lightweight accumulator that replaces the raw
  `pending_claims: list[Claim]` + `_add()` closures.

These are shared utilities, not a shared base class. Each ingest command
retains its own `handle()` and source-specific logic.

Success criteria:

- Duplicated manufacturer resolution consolidated into one implementation
- No regression in either ingest command's output

## Validation Strategy

Validation already exists in `validate_catalog.py` and
`data/explore/04_checks.sql`. This refactor should strengthen validation
rather than replace it.

### Input validation (Phases 1, 2, and 3)

Before source-specific normalization begins:

- required top-level keys exist (enforced by `from_raw()` factories)
- known record-type flags are present where expected
- important nested objects have required fields
- errors categorized as `ParseError` vs `MatchError`

### Output validation (ongoing)

After normalization and/or persistence:

- no orphaned relationship targets
- no self-referential or chained `variant_of`
- no unresolved FK claim values for authoritative source outputs
- summary counts for auto-created taxonomy / low-confidence mappings
- diff-oriented reporting when ingest behavior changes materially

### Golden records as a refactoring safety net

Run `validate_catalog` before and after each phase to confirm behavioral
equivalence. Over time, make golden records more intentional: add edge-case
cohorts (aliases that should collapse, conversions, split OPDB groups,
no-IPDB records, franchise-linked titles, known clone/non-variant cases)
rather than only famous machines.

## DuckDB Guidance

DuckDB's long-term role is as a querying layer, not a transform engine.

- **Raw source inspection** (`01_raw.sql`): Read raw JSON dumps to understand
  what OPDB/IPDB actually sent. This stays permanently.

- **Intermediate querying** (replaces `02_staging.sql`): Read files exported
  by the Python pipeline to ask questions about transformed data — "which
  aliases became clones?", "what did manufacturer resolution produce?" — without
  reimplementing the transforms in SQL.

- **Secondary validation** (`04_checks.sql`): Structural integrity checks
  (duplicate keys, orphan FKs, variant chains) that complement
  `validate_catalog`. Keep these.

DuckDB should not:

- re-implement canonical manufacturer resolution
- derive Pinbase relationship semantics independently
- act as a second source of truth for normalized catalog logic

## Risks and Tradeoffs

- Refactoring around explicit intermediate records may feel slower at first
  because it moves hidden assumptions into code that must be named.
- Some current heuristics may turn out to be too ambiguous to preserve as
  fully automatic behavior.
- Splitting logic into modules can become over-engineering if done all at once.
  The work should proceed only when each extraction makes a real hotspot simpler.
- The DuckDB simplification (Phase 4) requires the Python export to be
  reliable before the SQL transforms can be removed. During transition, both
  may coexist temporarily.

## First Step

Start with Phase 1: OPDB relationship extraction in
`backend/apps/catalog/ingestion/opdb_relationships.py`, introducing typed
`OpdbRecord` records as part of that work.

Do not begin with a repo-wide framework change. The first step is narrow:

- define `OpdbRecord` with a `from_raw()` factory for the fields that matter
  to alias/variant/clone classification
- extract the relationship classification logic into `opdb_relationships.py`
  with explicit `RelationshipCandidate` and `ReviewIssue` records
- preserve current DB outputs
- run `validate_catalog` to confirm nothing changed

If this makes the OPDB alias path easier to understand and maintain, use the
same pattern for the rest of the ingest pipeline. If not, reassess.
