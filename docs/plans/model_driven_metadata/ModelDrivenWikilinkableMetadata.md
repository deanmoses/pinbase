# Wikilinkable Model

## Context

This work is an instance of the broader pattern in [ModelDrivenMetadata.md](ModelDrivenMetadata.md): encode per-model behavior on the model itself, consume it generically from shared infrastructure. It's adjacent to but separate from [ModelDrivenLinkability.md](ModelDrivenLinkability.md) — see "Why this is separate from `LinkableModel`" below.

`WikilinkableModel` is a new abstract base that catalog models inherit to participate in the **wikilink autocomplete picker** — the popup that appears when a user types `[[` in a markdown textarea, letting them choose a type and then autocomplete a target row of that type. The wikilink system itself stays model-agnostic; it consumes a registry of `LinkType` entries built once at app-ready time by walking `WikilinkableModel.__subclasses__()`.

**Scope**: this plan covers the _authoring picker_ registration only. The markdown-ref _validator_ (`ingest_pinbase.validate_cross_entity_wikilinks`) is a separate walk over `CatalogModel`. Every catalog entity is a valid `[[type:id]]` target even when not picker-offered — Location renders fine in markdown but is suppressed from the picker.

**Sequencing**: this plan ships _after_ [ModelDrivenLinkability.md](ModelDrivenLinkability.md)'s Location-promotion follow-up lands. That earlier work makes Location a `CatalogModel`, which lets this plan frame the picker opt-in cleanly: every `CatalogModel` is a candidate, `WikilinkableModel` declares which ones actually appear.

## The contract

```python
from apps.core.schemas import LinkTargetSchema


def _default_link_serialize(obj: Any) -> LinkTargetSchema:
    return LinkTargetSchema(ref=obj.public_id, label=str(obj.name))


class WikilinkableModel(LinkableModel):
    """A linkable model that appears in the wikilink autocomplete picker."""

    link_sort_order: ClassVar[int] = 100
    link_label: ClassVar[str] = ""        # filled in at registration if empty
    link_description: ClassVar[str] = ""  # filled in at registration if empty
    link_autocomplete_search_fields: ClassVar[tuple[str, ...]] = ("name__icontains",)
    link_autocomplete_ordering: ClassVar[tuple[str, ...]] = ("name",)
    link_autocomplete_select_related: ClassVar[tuple[str, ...]] = ()
    link_autocomplete_serialize: ClassVar[Callable[[Any], LinkTargetSchema]] = (
        staticmethod(_default_link_serialize)
    )
```

- `link_sort_order` — default `100`. Display order in the wikilink picker (lower = earlier).
- `link_label` — default empty; filled at registration time with `str(model._meta.verbose_name).title()`. Human-readable type label in the picker.
- `link_description` — default empty; filled at registration time with `f"Link to a {model._meta.verbose_name}"`. One-liner description shown alongside the label.
- `link_autocomplete_search_fields` — default `("name__icontains",)`. Django ORM filter spec for autocomplete queries against the type's rows.
- `link_autocomplete_ordering` — default `("name",)`. Django ORM ordering for autocomplete results.
- `link_autocomplete_select_related` — default `()`. `select_related()` kwargs for autocomplete queries.
- `link_autocomplete_serialize` — default `_default_link_serialize` (declared on `WikilinkableModel`), wrapped in `staticmethod` so it doesn't bind `self` on instance access. Callback that converts a row to a `LinkTargetSchema`. Override only when the standard `(public_id, name)` shape doesn't apply; overrides should also be `staticmethod` (or a plain function assigned via `staticmethod(...)`) for the same reason.

Subclasses declare overrides where needed:

```python
class Title(CatalogModel, SluggedModel, TimeStampedModel, WikilinkableModel):
    link_sort_order: ClassVar[int] = 10
```

`link_label` and `link_description` cannot be derived in `__init_subclass__`: that hook fires before Django's `ModelBase` wires `_meta` (documented at [`apps/core/models.py:314`](../../backend/apps/core/models.py#L314)), so `model._meta.verbose_name` is unavailable. They're instead filled in by the registration loop in `apps/catalog/apps.py:_register_link_types` — at app-ready time, when `_meta` is fully wired — using the empty string on the base as the "use the default" sentinel:

```python
label = cls.link_label or str(cls._meta.verbose_name).title()
description = cls.link_description or f"Link to a {cls._meta.verbose_name}"
```

Defaults are still owned by `WikilinkableModel` (the empty string is the contract), but the materialization is deferred until `_meta` exists. No `getattr` and no consumer-side hardcoding of the fallback string — both lines are unconditional.

Discovery uses the existing [`catalog_app_subclasses`](../../backend/apps/catalog/_walks.py) helper called with `WikilinkableModel` — same idiom the registration loop uses today (just with a different base). It walks Django's app registry, filters out abstracts, and scopes to the catalog app. No hand-maintained list of who participates; inheriting `WikilinkableModel` opts the model into the picker, not inheriting it keeps the model out. The app registry handles abstract intermediates (e.g. `CatalogModel`) that bare `__subclasses__()` would silently drop. Catalog-scoping matches the picker's domain — the picker only lists catalog entity types — and matches the rationale in §Why this lives in `apps.core.models`.

### MRO diamond on `LinkableModel`

After the hoist, every catalog model that joins the picker has two paths to `LinkableModel` — one via `CatalogModel` (which aggregates `LinkableModel + LifecycleStatusModel + ClaimControlledModel`) and one via `WikilinkableModel(LinkableModel)`. Python's C3 linearization handles the diamond cleanly. `WikilinkableModel` does **not** add an `__init_subclass__` (label/description derivation is deferred to registration time per the previous section), so only `LinkableModel.__init_subclass__` runs per concrete subclass — and it's resolved via MRO lookup once per class definition, regardless of how many paths reach `LinkableModel`. No re-entry issues to design around.

## Why this is separate from `LinkableModel`

`LinkableModel` answers "what's this model's URL identity?" — `entity_type`, `entity_type_plural`, `public_id_field`, `link_url_pattern`. Every model that has URLs declares this.

`WikilinkableModel` answers "should this type appear in the wikilink picker, and how?" — picker label, sort order, autocomplete config. Only types that the editorial UI exposes for wikilinking declare this. **Location is the live case**: it's a `CatalogModel` (URL-addressable, claim-controlled, lifecycle-tracked) but the editorial UI suppresses it from the picker, so it does not inherit `WikilinkableModel`. A future admin-only or internal-only linkable model would do the same.

This matches the umbrella's [one capability per base](ModelDrivenMetadata.md#pattern-base-class--mixin) rule. Linkability and wikilinkability are independent capabilities, even though one depends on the other (you must be linkable to be wikilinkable; `WikilinkableModel` enforces this by inheriting from `LinkableModel`).

It also keeps the wikilink system itself model-agnostic. The wikilink registry doesn't know about Title or Manufacturer; it just walks `WikilinkableModel` subclasses and reads each one's declared ClassVars. Editorial decisions ("Title appears first in the picker") live on the model class as the source of truth — not in a hand-maintained registry inside the wikilink layer.

## Current state and hoist plan

What this plan accomplishes, summarized:

1. Picker config moves from scattered `getattr` ClassVars on `LinkableModel` to a typed contract on a dedicated `WikilinkableModel` base — the umbrella's [base class / mixin](ModelDrivenMetadata.md#pattern-base-class--mixin) pattern, with no `getattr` fallbacks.
2. Picker membership flips from "every concrete `LinkableModel` minus a sentinel" to explicit opt-in by inheritance — so Location stays out of the picker structurally, not via a `link_autocomplete_serialize = None` override.
3. **The two model-keyed registries — `_ENTITY_TYPE_MAP` ([`core/entity_types.py`](../../backend/apps/core/entity_types.py)) and the `LinkType` registry ([`core/markdown_links.py`](../../backend/apps/core/markdown_links.py)) — converge on a single canonical name per model: `entity_type` (kebab-case singular).** Today the `LinkType` registry keys on `__name__.lower()` (e.g. `gameplayfeature`) while `_ENTITY_TYPE_MAP` keys on `entity_type` (`gameplay-feature`); same models, divergent keys, no enforcement that they agree. Step 3 below collapses that divergence — and the markdown-ref validator [`ingest_pinbase.validate_cross_entity_wikilinks`](../../backend/apps/catalog/management/commands/ingest_pinbase.py) flips with it, so pindata's authored `[[gameplay-feature:foo]]` resolves to the same row in the renderer, the validator, and the entity-type lookup.

The wikilink registration loop in [`apps/catalog/apps.py`](../../backend/apps/catalog/apps.py) iterates `apps.get_app_config("catalog").get_models()`, filters by `issubclass(model, LinkableModel)`, and reads picker config via `getattr(model, "link_*", default)` for six different attrs — the [field-on-model antipattern](ModelDrivenMetadata.md#antipattern-field-on-model) shape, six call sites, untyped, with consumer-side fallbacks.

Declarations today:

- `link_sort_order = 10/20/30/40` declared bare on Title, MachineModel, Manufacturer, Person.
- `link_type_name`, `link_label`, `link_description`, `link_autocomplete_*` — zero declarations; every model uses the registry's fallback.

Hoist:

1. Add `WikilinkableModel(LinkableModel)` to `apps/core/models.py` with the seven typed ClassVars from §The contract — including `link_autocomplete_serialize`, which carries `_default_link_serialize` as the base-level default. Move `_default_serialize` (currently a closure inside `_register_link_types` at [`apps/catalog/apps.py:43-46`](../../backend/apps/catalog/apps.py)) into `apps/core/models.py` near `WikilinkableModel` as `_default_link_serialize`. **Do not add an `__init_subclass__`** — `_meta` isn't wired yet at that point; registration-time materialization (next paragraph) handles label/description.
2. **Strip the "Class attributes for link registration (all optional)" block** from `LinkableModel`'s docstring. Today's class body never actually declared those attrs — the docstring just listed them as recognized override hooks. The hooks move to `WikilinkableModel`, so the block becomes misleading and should go away (or be replaced with a one-line pointer to `WikilinkableModel` for picker presentation).
3. **Drop `link_type_name` entirely.** Zero declarers in code; the registry can use `model.entity_type` (already on `LinkableModel`) as the registry name. No need for an unused override hook. Also update the validator at [`ingest_pinbase.validate_cross_entity_wikilinks`](../../backend/apps/catalog/management/commands/ingest_pinbase.py): after the Linkability PR landed it walks `CatalogModel` and keys lookups on `public_id_field`, but it still derives the link-type key via `getattr(model, "link_type_name", model.__name__.lower())` to stay consistent with the renderer. This step replaces that with `model.entity_type` directly — the same swap the renderer's registration loop is making, so the two stay in lockstep. (The corresponding pindata-side rewrite — flipping authored references from `[[gameplayfeature:...]]` to `[[gameplay-feature:...]]` etc. — has already shipped and is live in R2; both swaps are safe to land together.)
4. Make Title, MachineModel, Manufacturer, Person inherit `WikilinkableModel`. Their existing `link_sort_order` declarations become typed overrides of the base default.
5. **Make every other current picker member inherit `WikilinkableModel`**, enumerated explicitly so the migration is mechanical and no model is silently dropped from the picker.

   Today's picker membership (every concrete `LinkableModel` in catalog, minus Location-via-sentinel) — verified by walking `apps.get_app_config("catalog").get_models()` filtered by `issubclass(model, LinkableModel)`:
   - **Already listed in step 4**: `Title`, `MachineModel`, `Manufacturer`, `Person`.
   - **Added in step 5**: `CorporateEntity`, `System`, `TechnologyGeneration`, `TechnologySubgeneration`, `DisplayType`, `DisplaySubtype`, `Cabinet`, `GameFormat`, `RewardType`, `Tag`, `CreditRole`, `Theme`, `GameplayFeature`, `Franchise`, `Series`.

   Post-hoist target: the union of those two lists. **Location does not inherit `WikilinkableModel`** — it stays a `CatalogModel` and stays out of the picker by virtue of the absent inheritance. Re-derive both lists from `_register_link_types`'s actual registered set immediately before implementing, in case a new entity has been added since this plan was written.

6. Replace the registration loop in `catalog/apps.py` with a walk over `catalog_app_subclasses(WikilinkableModel)` (same helper the loop uses today against `LinkableModel`), using direct attribute access on `WikilinkableModel`'s ClassVars (with the `link_label`/`link_description` registration-time materialization shown in §The contract). No `getattr` fallbacks, no `issubclass` filter. The `_default_serialize` closure inside `_register_link_types` is also gone — the loop reads `cls.link_autocomplete_serialize` directly off the class because `WikilinkableModel` declares the default. Class-level access (not instance-level) is what makes the `staticmethod` wrapping in §The contract a defensive belt-and-suspenders, not a strict requirement at this call site.
7. **Remove the `link_autocomplete_serialize = None` sentinel** from [`apps/catalog/models/location.py`](../../backend/apps/catalog/models/location.py). Today that sentinel is how Location is suppressed from the picker. Suppression is now structural (Location doesn't inherit `WikilinkableModel`), so the sentinel is dead — the `getattr(..., _default_serialize)` consumer that read it is also gone (replaced in step 6 by direct attribute access on the base-level default).

No semantic change to the picker's offered set or rendered behavior. Existing tests covering the registry and the picker UI carry over.

New tests:

- **Negative**: a synthetic `LinkableModel` subclass that does not inherit `WikilinkableModel` is absent from the registry.
- **Parity (membership guard)**: a test that pins the registered picker types to the explicit post-hoist target list from step 5. Capture the registered set today (e.g. `sorted(lt.name for lt in get_enabled_link_types())`) before the hoist, hard-code that list as the expected value, and assert equality after the hoist. This catches a missed `WikilinkableModel` inheritance on any of the 19 entities — the failure mode the implicit-include → explicit-opt-in flip introduces.
- **Default serializer**: assert that an entity without an explicit `link_autocomplete_serialize` override still produces a `LinkTargetSchema(ref=public_id, label=name)` from the base-level default (locks in §1's `_default_link_serialize` move onto `WikilinkableModel`).
- **Renderer/validator resolution parity**: for each registered `LinkType`, assert that the wikilink validator and the markdown renderer agree on the lookup — same key, same `public_id_field`, same model. Membership parity (the test above) catches "did this type get registered at all"; this catches "do the two consumers of the registry resolve `[[type:id]]` to the same row." This is the test class that would have caught the validator/renderer divergence latent before the LocationCatalog PR's wikilink test additions; it generalizes those tests across every type rather than spot-checking one.

## Verification

1. **Pre-flight grep** (before deleting `link_type_name` in step 3)
   - `grep -rn "link_type_name" .` across the whole repo (backend Python, frontend TS/Svelte, tests, docs). Today's known sites are the `LinkableModel` docstring at [`backend/apps/core/models.py`](../../backend/apps/core/models.py), the picker loop at [`backend/apps/catalog/apps.py`](../../backend/apps/catalog/apps.py), and the validator at [`backend/apps/catalog/management/commands/ingest_pinbase.py`](../../backend/apps/catalog/management/commands/ingest_pinbase.py) — all three are removed/replaced by this plan. If a new caller has appeared since this plan was written, address it before deletion.
1. **Tests**
   - `cd backend && uv run pytest` — full backend suite. Particular eyes on `apps/catalog/tests/` for picker-registry tests and any test that checks specific `LinkType` membership.
   - The new test described above: a synthetic `LinkableModel` subclass that does not inherit `WikilinkableModel` is absent from the registry.
1. **API regen**
   - `make api-gen` — regenerate `frontend/src/lib/api/schema.d.ts` and `frontend/src/lib/api/catalog-meta.ts`. `catalog-meta.ts` reads `_meta.verbose_name` directly (not `link_label`), so it should be byte-identical post-hoist; regen anyway as cheap insurance against an emitted shape we haven't traced.
1. **Smoke**
   - `make dev`, then exercise the wikilink picker in a markdown editor. Confirm: every entity in the post-hoist target list appears in the picker; Location does not; the existing `link_sort_order` overrides on Title/MachineModel/Manufacturer/Person still control the displayed order.
1. **Lint**
   - `make lint` — ruff + ESLint clean.

## Why this lives in `apps.core.models`

`WikilinkableModel` is a catalog-app-aware concept (the picker only lists catalog entity types), but the class itself is generic Django infrastructure. Living in `apps/core/models.py` alongside `LinkableModel` keeps the linkability/wikilinkability stack co-located. Catalog models import and inherit from it; the wikilink registration loop in `catalog/apps.py` walks its subclass set.
