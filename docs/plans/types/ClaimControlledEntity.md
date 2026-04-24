# ClaimControlledEntity Base

Extract the shared contract between `CatalogModel` and `Location` into a typed abstract base so that claim-resolver helpers (and any other code that operates generically over claim-controlled entities) can accept all of them under one static type.

Follow-up to [CatalogResolveBaselineCleanup.md](CatalogResolveBaselineCleanup.md). During that plan's revision, the helpers were retyped to `type[CatalogModel]` — which covers 19/20 callers. `Location` is the outlier and is cast at 2 call sites with a comment pointing at this plan.

The headline payoff is **not** the two disappearing casts — it's collapsing 20+ duplicated `claims = GenericRelation("provenance.Claim")` declarations into one canonical site and giving generic helpers a typed contract for "anything claim-controlled." The cast removal is a minor follow-on.

## Problem

Every claim-controlled catalog entity declares the same set of attributes:

- `claims = GenericRelation("provenance.Claim")` — reverse accessor to provenance claims. Duplicated verbatim on 20+ concrete models today (see `grep -rn 'claims = GenericRelation' backend/apps/catalog/models/`).
- `slug: SlugField(...)` — short URL-safe identifier. Uniqueness and max-length vary.
- `name: CharField(...)` — human-readable label. Max-length and validators vary.
- Optional `extra_data: JSONField` — unmatched-claim staging dict on a subset.

`CatalogModel` (via `LinkableModel`) declares typed `name: str` / `slug: str` at the abstract base level — which is why generic code that takes `type[CatalogModel]` can read those attributes without per-callsite casts. But `CatalogModel` also requires `entity_type` / `entity_type_plural` declarations (because `LinkableModel` is about _public URL-addressable_ entities) and inherits `SluggedModel`'s globally-unique `slug`.

`Location` deliberately opts out of that contract:

- Its `slug` is not globally unique — two different countries can both have cities with slug `springfield`. Uniqueness is scoped to `location_path` instead.
- It has no `entity_type` / `entity_type_plural` — Location is not a first-class URL-addressable catalog entity in the same way `MachineModel` or `Manufacturer` are.

So `Location` sits outside the `LinkableModel`/`CatalogModel` hierarchy even though, for the purposes of the claim resolver, it satisfies the same contract: it has `claims`, `slug`, `name`, and its fields are claim-controlled.

The consequences today:

- Generic helpers that want to operate on "any claim-controlled entity" have to pick between (a) `type[CatalogModel]` plus a cast at each Location call site, (b) `type[models.Model]` plus `_default_manager` swaps and scattered attribute ignores, or (c) a `runtime_checkable` Protocol. The Protocol option works for `slug: str` / `name: str` but breaks down on `claims` — `GenericRelation` is a descriptor whose runtime type (`RelatedManager`) is constructed per-class, and Protocols can't express "this attribute is a descriptor that resolves to a per-class generic manager." That `claims` requirement is the load-bearing reason an abstract base wins over a Protocol here, not a general dismissal of Protocols.
- The `claims = GenericRelation("provenance.Claim")` declaration is copy-pasted across 20+ models — no single place to change if the GenericRelation configuration ever needs to shift (e.g. `related_query_name`).
- Static type checkers can't express "anything claim-controlled" — every new such helper either accepts the looser type or invents a new cast site.

## Approach

Introduce a new abstract base — `ClaimControlledEntity` — in `apps/provenance/models/`. Provenance owns `Claim`, owns the `GenericRelation` target, and has consumers of its own (the `type[models.Model]` annotations scattered through [provenance/validation.py](../../../backend/apps/provenance/validation.py) are really "type[ClaimControlledEntity]" in disguise). "Anything that has claims" is a provenance-shaped abstraction, not a core or catalog one.

**App-boundary note.** Per [AppBoundaries.md](../../AppBoundaries.md), `core` depends on nothing — even string-reference dependencies. `apps/core/models.py` cannot host `GenericRelation("provenance.Claim")`. Provenance is the correct home; catalog already depends on provenance, so catalog models can inherit cleanly.

**Hierarchy shape.** `LinkableModel` stays in `core` untouched — it's about URL-addressability, not claims. Concrete catalog models multi-inherit at the leaf:

- `CatalogModel(LinkableModel, EntityStatusMixin, ClaimControlledEntity)` — picks up URL-addressability, status, and claim-control.
- `Location(EntityStatusMixin, ClaimControlledEntity)` — claim-controlled and status-tracked, but not URL-addressable.

The original draft proposed `ClaimControlledEntity(EntityStatusMixin)` so the two concepts collapsed into one chain. Multi-inherit instead — `EntityStatusMixin` and `ClaimControlledEntity` are independent concerns and conflating them in a single chain bakes in a coupling we don't want at the type level.

```python
# apps/provenance/models/_base.py (or similar)

class ClaimControlledEntity(models.Model):
    """Abstract base for entities whose display fields are claim-controlled.

    Declares the reverse-accessor to provenance claims and the typed ``slug``
    / ``name`` shape that claim-resolver helpers read generically.  Does NOT
    imply URL-addressability, globally-unique slugs, or status tracking —
    those are ``LinkableModel`` / ``SluggedModel`` / ``EntityStatusMixin``
    concerns and are layered in independently at the concrete class.
    """

    # Instance-level annotations let ``type[ClaimControlledEntity]`` code read
    # ``.slug`` / ``.name`` without casting.  Concrete subclasses declare the
    # actual CharField / SlugField with their own max_length and validators.
    slug: str
    name: str

    claims = GenericRelation("provenance.Claim")

    class Meta:
        abstract = True
```

Then:

- `CatalogModel`: change from `class CatalogModel(LinkableModel, EntityStatusMixin)` to `class CatalogModel(LinkableModel, EntityStatusMixin, ClaimControlledEntity)`. `LinkableModel` itself is unchanged.
- `Location`: change from `class Location(EntityStatusMixin, models.Model)` to `class Location(EntityStatusMixin, ClaimControlledEntity)`.
- Remove `claims = GenericRelation("provenance.Claim")` from every concrete catalog model (20+ sites) — now inherited.

Once those are in place, generic helpers switch from `type[CatalogModel]` (or `type[models.Model]`) to `type[ClaimControlledEntity]`:

- The 2 Location casts in [catalog/resolve/\_\_init\_\_.py:197](../../../backend/apps/catalog/resolve/__init__.py#L197) and [catalog/resolve/\_relationships.py](../../../backend/apps/catalog/resolve/_relationships.py) disappear.
- Provenance helpers that take `type[models.Model]` for claim-bearing entities (see `validation.py` lines 65, 74, 91, 175, 227, 333, 349, 449, 453, 548, 557, 629) can tighten to `type[ClaimControlledEntity]`.
- Downstream code that inspects `.claims` generically gains a typed contract.

## Things to verify before implementing

- **`GenericRelation` inheritance semantics.** Django's `GenericRelation` is a descriptor; confirm it survives abstract-base inheritance cleanly (it should, given how many projects do this). Run the migration and check that removing the per-model declaration doesn't produce a phantom migration.
- **Check-constraint name collisions.** Concrete subclasses use `field_not_blank("slug")` / `slug_not_blank()` which embed `%(app_label)s_%(class)s` — those stay on the concrete subclass, so no collision. But verify that no `constraints` list on a subclass refers to `slug` in a way that collides with anything the new base might add (the proposed base adds nothing).
- **`claims_exempt` / `claim_fk_lookups`.** These are concrete-class `ClassVar`s and stay on the concrete subclass. The new base does not declare them. Confirm `get_claim_fields` still works against the new hierarchy (it introspects `model_class._meta.get_fields()` which is unaffected).
- **Manager compatibility.** `CatalogManager[Self]` is declared on `EntityStatusMixin` (see [core/models.py:248](../../../backend/apps/core/models.py#L248)), so every concrete subclass that mixes in `EntityStatusMixin` — including `Location` — already has `CatalogManager`, not the default `models.Manager`. The new `ClaimControlledEntity` base should NOT declare `objects`; the existing `EntityStatusMixin`-supplied manager continues to apply unchanged.
- **Existing typing on `LinkableModel`.** `LinkableModel` already declares `name: str` / `slug: str`. With multi-inheritance at the leaf (`CatalogModel(LinkableModel, ..., ClaimControlledEntity)`), both bases declare the same annotations — harmless but redundant at the MRO level. Leave `LinkableModel`'s declarations alone for this PR; touching `core` purely for cosmetic dedup expands the diff without payoff.
- **MRO and `Meta` inheritance.** Multi-inheriting two abstract bases (e.g. `EntityStatusMixin` and `ClaimControlledEntity`) is standard Django but verify Django doesn't complain about ambiguous `Meta` resolution. Both should declare only `abstract = True`, so there's nothing to merge.

## Scope and ordering

Land the structural change as a single atomic commit — model edits, removed declarations, and migration together — so the "migration is empty" invariant is verifiable in one diff:

1. Add `ClaimControlledEntity` to `apps/provenance/models/` (new module, exported from the `provenance.models` package).
2. Add `ClaimControlledEntity` to `CatalogModel`'s and `Location`'s base lists at the leaf (multi-inherit alongside the existing bases).
3. Remove 20+ `claims = GenericRelation("provenance.Claim")` declarations from concrete catalog models.
4. Run `makemigrations`. The expected result is **no new migration** — pulling a `GenericRelation` to an abstract base is a Python-only change with no DDL impact. If Django _does_ emit a migration, **stop and investigate** before committing; a non-empty migration here means something about the field config differs and the rollover isn't actually a no-op.
5. **Prerequisite before any helper widening: fix the single-object slug-conflict guard.** [catalog/resolve/\_entities.py:293-309](../../../backend/apps/catalog/resolve/_entities.py#L293) does an unguarded `model_class.objects.filter(slug=obj.slug).exclude(pk=obj.pk).exists()` and silently reverts on hit. That's safe today because every caller passes a `CatalogModel` subclass with a globally-unique slug. The bulk path at [\_entities.py:197](../../../backend/apps/core/models.py#L197) already gates on `slug_field.unique`; mirror the same gate on the single-object path _before_ widening the type. Without this fix, Location resolution would silently revert legitimate same-slug cities in different `location_path`s.
6. Flip helper signatures in `catalog/resolve/*.py` from `type[CatalogModel]` to `type[ClaimControlledEntity]`; flip provenance helpers in `validation.py` from `type[models.Model]` to `type[ClaimControlledEntity]` where they specifically operate on claim-bearing entities.
7. Remove the 2 Location casts and their follow-up comments.

Keep this PR purely structural — see "Reuse" below for tempting additions to defer.

## Non-goals

- Does NOT promote `Location` to `CatalogModel` / `LinkableModel`. Location's non-unique slug and non-public-addressability are real semantic differences that the narrower base respects.
- Does NOT unify the `extra_data` field — it remains per-model (some have it, some don't) and stays behind the existing `hasattr(obj, "extra_data")` runtime guard in the resolver.
- Does NOT introduce a shared manager class. `CatalogManager[Self]` continues to come from `EntityStatusMixin` for every entity that mixes it in (including both `CatalogModel` subclasses and `Location`). The new `ClaimControlledEntity` base does not declare `objects`.

## Verification

- `./scripts/mypy` — baseline `new: 0`. Several `attr-defined` / `arg-type` entries in `catalog/resolve/*.py` and any downstream caller that narrowed around the CatalogModel/Location split should drop.
- `uv run --directory backend pytest apps/catalog/tests/ apps/core/tests/ apps/provenance/tests/` — behavior-preserving; the migration should be a no-op and all resolver tests should pass.
- `uv run --directory backend python manage.py makemigrations --dry-run` — verify no surprise migrations after the GenericRelation pull-up.

## Reuse

The new base is the canonical home for _any_ future attribute that is universal across claim-controlled entities. Candidates to consider:

- `validate_check_constraints` as a method on the base.
- `resolve()` shortcut delegating to `resolve_entity`.
- `claims_exempt: ClassVar[frozenset[str]] = frozenset()` with the default declared once.

**Explicitly NOT in the initial PR.** The initial PR is purely structural: add the base, pull up `GenericRelation`, retype helpers, remove casts. Adding behavior to the base in the same change makes the "migration is empty / no behavior change" invariant much harder to verify in review, and bundles a refactor with a feature. Each of the candidates above is its own follow-up PR.

## Out-of-scope follow-ups

- **Provenance `.claims` reverse accessors in other apps.** If any non-catalog code accesses `.claims` on a mixed set of catalog entities, it can also tighten to `ClaimControlledEntity`. Grep before the flip to surface them.
- **Claim-field registry.** `get_claim_fields` currently takes `type[models.Model]`; once the base exists, narrowing to `type[ClaimControlledEntity]` makes the contract explicit. Low priority.
