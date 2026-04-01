# Data Modeling

Principles and conventions for Django models in Pinbase.

## Principles

### Validate strictly, validate early

Add the strictest constraint you can defend. Relaxing a constraint is a one-line migration. Tightening one means auditing every existing row and hoping nothing breaks — so start strict.

### Validate in the database

Push as much validation as you can to the database. Django has multiple code paths that skip Python validation (`objects.create()`, `bulk_create()`, `update()`, management commands, raw SQL, migrations). A CHECK constraint catches all of them.

### Default to PROTECT on foreign keys

`on_delete=PROTECT` blocks deletion of a referenced row. This is the safe default — it forces you to handle the dependency explicitly rather than silently losing data. Use `CASCADE` only for wholly owned children (e.g., `MediaVariant` belongs to `MediaAsset` — deleting the asset should delete its variants). Never use `SET_NULL` unless there's a clear product reason to preserve the row without its parent.

## Django Pitfalls

These are the specific reasons we enforce constraints at the DB level rather than relying on Django's Python-layer validation:

- **`CharField(blank=False)`** is only enforced at `full_clean()`, not at the DB level. Use `field_not_blank()` from `apps.core.models` to add a CHECK constraint.
- **`PositiveIntegerField`** allows 0. If you need `> 0`, add a CHECK constraint.
- **`choices=`** on CharField is only enforced at `full_clean()`. Add a CHECK constraint (`field__in=[...]`) to enforce valid values at the DB level.
- **`objects.create()`** bypasses `full_clean()` entirely. Without DB constraints, invalid data enters the database from management commands, migrations, bulk operations, and raw SQL.

## Conventions

### Timestamps

Inherit from `TimeStampedModel` (in `apps.core.models`) for `created_at` / `updated_at`. Don't define these fields manually.

### GenericForeignKey

Use `PositiveBigIntegerField` for `object_id` to match `BigAutoField` PKs. Use `on_delete=PROTECT` on the `ContentType` FK.

### Constraint naming

Use explicit names: `{app}_{model}_{description}`. Never rely on Django's auto-generated names.

Cross-field constraints use `violation_error_code="cross_field"`.

### Range and enum constants

Define range bounds and enum values as module-level constants. Reference them from both validators and constraints so they can't drift apart. See `test_constraint_drift.py` for the meta-test that enforces this.

### Storage keys

Store relative paths, never full URLs. The storage prefix (e.g., `media/`) is enforced in application code, not DB constraints, so the storage location stays configurable without schema changes.

### No regex in CHECK constraints

`__startswith`, `__contains`, and `__endswith` generate standard SQL `LIKE`, which works identically on PostgreSQL and SQLite. Use these in CHECK constraints.

**Do not use `__regex` in CHECK constraints.** On SQLite, `__regex` generates `REGEXP`, which depends on a Python function that Django registers on the connection. It works during normal Django operations, but anything that touches the database outside Django (DB browsers, backup restores, raw migration scripts) won't have the function — causing "no such function: regexp" errors or silently unenforced constraints.

If a pattern can't be expressed with LIKE, enforce it in Django model validation instead of a CHECK constraint.

## Testing DB Constraints

Use `objects.create()` with `pytest.raises(IntegrityError)`. Django's `create()` bypasses `full_clean()`, so invalid values hit the DB constraint directly. No raw SQL or `_raw_update` helper needed.

Test both directions:

- **Negative**: invalid data is rejected (the constraint fires).
- **Positive**: valid edge cases are accepted (the constraint doesn't over-reject).

```python
def test_byte_size_zero_rejected(self, user):
    with pytest.raises(IntegrityError):
        MediaAsset.objects.create(**_asset_kwargs(user, byte_size=0))

def test_valid_asset_without_dimensions(self, user):
    """Non-ready assets can omit dimensions."""
    asset = MediaAsset.objects.create(
        **_asset_kwargs(user, status="failed", width=None, height=None)
    )
    assert asset.pk is not None
```
