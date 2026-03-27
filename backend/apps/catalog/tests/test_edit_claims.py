"""Tests for shared claim-edit helpers."""

from __future__ import annotations

import pytest
from ninja.errors import HttpError

from apps.catalog.api.edit_claims import validate_scalar_fields
from apps.catalog.models import Title


@pytest.mark.django_db
class TestValidateScalarFields:
    def test_allows_clearing_nullable_and_blankable_fields(self):
        specs = validate_scalar_fields(
            Title,
            {
                "description": None,
                "franchise": None,
            },
        )

        assert {spec.field_name: spec.value for spec in specs} == {
            "description": "",
            "franchise": "",
        }

    def test_rejects_clearing_required_string_fields(self):
        with pytest.raises(HttpError, match="cannot be cleared"):
            validate_scalar_fields(Title, {"name": None})
