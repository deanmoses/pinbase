"""Tests for name↔alias cross-uniqueness.

For entity types with unique names and aliases (Manufacturer, Theme,
GameplayFeature, RewardType), the combined pool of names + alias values
must be unique (case-insensitive).  Series.name must also be unique.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import (
    GameplayFeature,
    GameplayFeatureAlias,
    Manufacturer,
    ManufacturerAlias,
    RewardType,
    RewardTypeAlias,
    Series,
    Theme,
    ThemeAlias,
)


# ---------------------------------------------------------------------------
# Series.name uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSeriesNameUnique:
    def test_unique_true_on_name_field(self):
        """Series.name must be declared unique=True (DB constraint enforced after migration)."""
        field = Series._meta.get_field("name")
        assert field.unique is True


# ---------------------------------------------------------------------------
# Alias value must not match any name in the parent entity table
# ---------------------------------------------------------------------------

ALIAS_CASES = [
    pytest.param(Manufacturer, ManufacturerAlias, "manufacturer", id="manufacturer"),
    pytest.param(Theme, ThemeAlias, "theme", id="theme"),
    pytest.param(
        GameplayFeature, GameplayFeatureAlias, "feature", id="gameplay_feature"
    ),
    pytest.param(RewardType, RewardTypeAlias, "reward_type", id="reward_type"),
]


@pytest.mark.django_db
class TestAliasCannotMatchName:
    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_alias_matching_existing_name_rejected(
        self, parent_cls, alias_cls, fk_attr
    ):
        """An alias value that matches another entity's name is rejected."""
        parent_cls.objects.create(name="Alpha", slug="alpha")
        parent_b = parent_cls.objects.create(name="Beta", slug="beta")
        alias = alias_cls(**{fk_attr: parent_b, "value": "Alpha"})
        with pytest.raises(ValidationError):
            alias.full_clean()

    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_alias_matching_own_name_rejected(self, parent_cls, alias_cls, fk_attr):
        """An alias matching its own parent's name is redundant and rejected."""
        parent = parent_cls.objects.create(name="Alpha", slug="alpha")
        alias = alias_cls(**{fk_attr: parent, "value": "Alpha"})
        with pytest.raises(ValidationError):
            alias.full_clean()

    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_alias_matching_name_case_insensitive(self, parent_cls, alias_cls, fk_attr):
        """The check is case-insensitive."""
        parent_cls.objects.create(name="Alpha", slug="alpha")
        parent_b = parent_cls.objects.create(name="Beta", slug="beta")
        alias = alias_cls(**{fk_attr: parent_b, "value": "ALPHA"})
        with pytest.raises(ValidationError):
            alias.full_clean()

    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_non_colliding_alias_accepted(self, parent_cls, alias_cls, fk_attr):
        """An alias that doesn't match any name is accepted."""
        parent = parent_cls.objects.create(name="Alpha", slug="alpha")
        alias = alias_cls(**{fk_attr: parent, "value": "Gamma"})
        alias.full_clean()  # should not raise


# ---------------------------------------------------------------------------
# Name must not match any alias value in the alias table
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNameCannotMatchAlias:
    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_name_matching_existing_alias_rejected(
        self, parent_cls, alias_cls, fk_attr
    ):
        """Renaming an entity to match an existing alias is rejected."""
        parent_a = parent_cls.objects.create(name="Alpha", slug="alpha")
        parent_b = parent_cls.objects.create(name="Beta", slug="beta")
        alias_cls.objects.create(**{fk_attr: parent_a, "value": "Gamma"})
        parent_b.name = "Gamma"
        with pytest.raises(ValidationError):
            parent_b.full_clean()

    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_name_matching_own_alias_rejected(self, parent_cls, alias_cls, fk_attr):
        """Renaming to match your own alias is rejected (redundant)."""
        parent = parent_cls.objects.create(name="Alpha", slug="alpha")
        alias_cls.objects.create(**{fk_attr: parent, "value": "Gamma"})
        parent.name = "Gamma"
        with pytest.raises(ValidationError):
            parent.full_clean()

    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_name_matching_alias_case_insensitive(self, parent_cls, alias_cls, fk_attr):
        """The check is case-insensitive."""
        parent_a = parent_cls.objects.create(name="Alpha", slug="alpha")
        parent_b = parent_cls.objects.create(name="Beta", slug="beta")
        alias_cls.objects.create(**{fk_attr: parent_a, "value": "gamma"})
        parent_b.name = "GAMMA"
        with pytest.raises(ValidationError):
            parent_b.full_clean()

    @pytest.mark.parametrize("parent_cls,alias_cls,fk_attr", ALIAS_CASES)
    def test_non_colliding_name_accepted(self, parent_cls, alias_cls, fk_attr):
        """A name that doesn't match any alias is accepted."""
        parent = parent_cls.objects.create(name="Alpha", slug="alpha")
        parent.name = "Delta"
        parent.full_clean()  # should not raise


# ---------------------------------------------------------------------------
# Resolver: aliases colliding with names are skipped
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestResolverSkipsNameCollisions:
    def test_resolver_skips_alias_matching_name(self):
        """_resolve_aliases skips aliases whose value matches an entity name."""
        from django.contrib.contenttypes.models import ContentType

        from apps.catalog.claims import build_relationship_claim
        from apps.catalog.resolve._relationships import _resolve_aliases
        from apps.provenance.models import Claim, Source

        source = Source.objects.create(
            name="test-src", source_type="editorial", priority=300
        )
        Manufacturer.objects.create(name="Gottlieb", slug="gottlieb")
        mfr_b = Manufacturer.objects.create(name="Williams", slug="williams")

        # Assert a claim that would create alias "Gottlieb" on mfr_b — collides with mfr_a's name
        ct_id = ContentType.objects.get_for_model(Manufacturer).pk
        claim_key, value = build_relationship_claim(
            "manufacturer_alias",
            {"alias_value": "gottlieb", "alias_display": "Gottlieb"},
        )
        pending = [
            Claim(
                content_type_id=ct_id,
                object_id=mfr_b.pk,
                field_name="manufacturer_alias",
                claim_key=claim_key,
                value=value,
            )
        ]
        scope = {(ct_id, mfr_b.pk)}
        Claim.objects.bulk_assert_claims(
            source,
            pending,
            sweep_field="manufacturer_alias",
            authoritative_scope=scope,
        )

        _resolve_aliases(Manufacturer, "manufacturer_alias")

        # The colliding alias should NOT have been created
        assert ManufacturerAlias.objects.filter(value__iexact="Gottlieb").count() == 0


# ---------------------------------------------------------------------------
# API-level validation: plan_alias_claims rejects collisions
# ---------------------------------------------------------------------------


try:
    from ninja.errors import HttpError as _HttpError  # noqa: F401

    _has_ninja = True
except Exception:
    _has_ninja = False

_skip_ninja = pytest.mark.skipif(not _has_ninja, reason="ninja/pydantic compat issue")


@_skip_ninja
@pytest.mark.django_db
class TestPlanAliasClaimsRejectsCollisions:
    def test_alias_colliding_with_name_rejected(self):
        """plan_alias_claims rejects an alias that matches an existing entity name."""
        from ninja.errors import HttpError

        from apps.catalog.api.edit_claims import plan_alias_claims

        Manufacturer.objects.create(name="Gottlieb", slug="gottlieb")
        mfr_b = Manufacturer.objects.create(name="Williams", slug="williams")

        with pytest.raises(HttpError, match="conflicts with an existing"):
            plan_alias_claims(
                mfr_b, ["Gottlieb"], claim_field_name="manufacturer_alias"
            )

    def test_non_colliding_alias_accepted(self):
        from apps.catalog.api.edit_claims import plan_alias_claims

        mfr = Manufacturer.objects.create(name="Williams", slug="williams")
        specs = plan_alias_claims(mfr, ["WMS"], claim_field_name="manufacturer_alias")
        assert len(specs) == 1


# ---------------------------------------------------------------------------
# API-level validation: validate_scalar_fields rejects name→alias collisions
# ---------------------------------------------------------------------------


@_skip_ninja
@pytest.mark.django_db
class TestValidateScalarFieldsRejectsCollisions:
    def test_name_colliding_with_alias_rejected(self):
        """validate_scalar_fields rejects a name that matches an existing alias."""
        from ninja.errors import HttpError

        from apps.catalog.api.edit_claims import validate_scalar_fields

        mfr = Manufacturer.objects.create(name="Williams", slug="williams")
        ManufacturerAlias.objects.create(manufacturer=mfr, value="WMS")

        with pytest.raises(HttpError, match="conflicts with an existing"):
            validate_scalar_fields(Manufacturer, {"name": "WMS"})

    def test_non_colliding_name_accepted(self):
        from apps.catalog.api.edit_claims import validate_scalar_fields

        Manufacturer.objects.create(name="Williams", slug="williams")
        specs = validate_scalar_fields(Manufacturer, {"name": "Stern"})
        assert len(specs) == 1
