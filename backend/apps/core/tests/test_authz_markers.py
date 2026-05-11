"""Unit tests for the authz marker decorators.

The route-inventory test exercises `requires` and `gated_inline`
indirectly via every classified route, but `public_mutation`'s
validation logic only has the success path covered there. These tests
also lock the marker contracts (`@requires` wraps and re-stamps;
`@gated_inline` and `@public_mutation` stamp without wrapping) so any
future change to those contracts fails loudly.
"""

from __future__ import annotations

import pytest

from apps.core.authz.markers import (
    gated_inline,
    get_gated_inline_activity,
    get_public_reason,
    get_required_activity,
    public_mutation,
    requires,
)
from apps.core.authz.types import Activity


class TestRequires:
    def test_stamps_activity_attribute(self) -> None:
        @requires(Activity.CATALOG_EDIT)
        def view(request) -> None: ...

        assert get_required_activity(view) is Activity.CATALOG_EDIT

    def test_returns_wrapped_callable_with_marker(self) -> None:
        # @requires now wraps and re-stamps; the returned object is a
        # different callable carrying the marker. Ninja resolves
        # `op.view_func` to this wrapped callable, so the inventory
        # walker sees the marker on the right object.
        def view(request) -> None: ...

        wrapped = requires(Activity.CATALOG_EDIT)(view)
        assert wrapped is not view
        assert get_required_activity(wrapped) is Activity.CATALOG_EDIT
        # `functools.wraps` preserves identity for Ninja's introspection.
        assert wrapped.__wrapped__ is view  # type: ignore[attr-defined]
        assert wrapped.__name__ == view.__name__


class TestGatedInline:
    def test_stamps_activity_attribute(self) -> None:
        @gated_inline(Activity.CLAIM_REVERT)
        def view() -> None: ...

        assert get_gated_inline_activity(view) is Activity.CLAIM_REVERT

    def test_returns_original_callable_unchanged(self) -> None:
        def view() -> None: ...

        assert gated_inline(Activity.CLAIM_REVERT)(view) is view


class TestPublicMutation:
    def test_stamps_reason_attribute(self) -> None:
        @public_mutation("session teardown")
        def view() -> None: ...

        assert get_public_reason(view) == "session teardown"

    def test_returns_original_callable_unchanged(self) -> None:
        def view() -> None: ...

        assert public_mutation("ok")(view) is view

    def test_empty_string_raises_at_decoration_time(self) -> None:
        with pytest.raises(ValueError, match="non-empty reason"):
            public_mutation("")

    def test_whitespace_only_raises_at_decoration_time(self) -> None:
        # Catches the "developer typed a space to silence the test" case.
        with pytest.raises(ValueError, match="non-empty reason"):
            public_mutation("   ")

    def test_non_string_raises_at_decoration_time(self) -> None:
        with pytest.raises(ValueError, match="non-empty reason"):
            public_mutation(None)  # type: ignore[arg-type]
