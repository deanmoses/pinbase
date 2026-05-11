# Python Development

## Typing

Code MUST be as strongly typed as possible.

The following smells are _sometimes_ legitimate, but are usually a sign the type can be tightened:

- Use of `Any`, `object`, `cast`, `isinstance`, `setattr`, `getattr`, `TYPE_CHECKING`, `# type: ignore`, `# noqa`
- `tuple[...]` with 3+ positional fields, or the same tuple shape repeated across modules

### Valid exceptions to strong types

Broad types are acceptable when required by a third party:

- Django management-command `**kwargs` / `**options`
- Django signal receivers and auth-backend hooks
- Django-Ninja dispatch edges where schemas validate runtime shape
- Third-party APIs that genuinely discard type information
- Unavoidable django-stubs limitations

Every exception needs a short reason at the use site.

### Choosing a data shape

- Use Ninja/Pydantic `Schema` for API request/response shapes
- Use `TypedDict` for internal dicts with stable keys
- Use `Protocol` for structural contracts
- Use `NamedTuple` or dataclass for records with named fields
- Do not use a type alias to hide positional tuple structure (e.g. `UserRow = tuple[int, str, datetime]`) — use a `NamedTuple` instead
- Do not use `dict[str, Any]` for JSON-shaped data:
  - Use `apps.core.types.JsonData` for read-side JSON mappings
  - Use `apps.core.types.JsonBody` for mutable/test-client JSON bodies

### Django typing idioms

For helpers generic over model classes, prefer `_default_manager` over `.objects`; django-stubs can see `_default_manager` on `type[Model]`.

Do not replace `obj.fk_id is not None` with `obj.fk is not None` just to satisfy mypy. The first is a column check; the second may fetch the related object. If you need the related object narrowed, bind it locally after the `_id` guard and assert it is not `None`.

For queryset-annotated attributes, prefer a narrow structural `Protocol` over widening the whole model to `Any`.

### Pydantic and Ninja

Serialization helpers should usually return Ninja/Pydantic `Schema` instances, not dicts that are later revalidated into the same schema.

Use dict returns only when the dict is the real runtime contract, such as cached JSON-byte hot paths.

When a Ninja response type is a union of schemas with shared fields, make dispatch structurally unambiguous: required distinguishing fields on the richer schema, and `extra="forbid"` on the minimal schema where needed.

### Suppressions

If you use `# type: ignore[code]` or `# noqa: RULE`, you MUST include a reason.

`ANN401` applies to top-level `Any` parameters and return annotations. It does not apply to nested `dict[str, Any]` or `cast(Any, ...)`; do not add `# noqa: ANN401` there. Use a plain comment if the broad type is intentional.

NEVER silence a warning when the underlying type can be expressed.
