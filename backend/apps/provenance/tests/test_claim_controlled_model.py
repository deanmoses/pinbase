"""Structural invariant: every claim-controlled catalog model inherits
``ClaimControlledModel`` and exposes a ``claims`` GenericRelation pointing
at ``Claim``.

Guards against a future leaf class being added (or rebased) without
``ClaimControlledModel`` in its bases — typecheck wouldn't catch it, and
existing validator coverage only inspects models that already have a
``claims`` relation, so a model that lost it would be invisible.
"""

from __future__ import annotations

from django.apps import apps
from django.db.models import Model

from apps.catalog.models import Location
from apps.core.models import CatalogModel
from apps.provenance.models import Claim, ClaimControlledModel


def _claim_controlled_catalog_models() -> list[type[Model]]:
    return [
        m
        for m in apps.get_app_config("catalog").get_models()
        if not m._meta.abstract and (issubclass(m, CatalogModel) or m is Location)
    ]


def test_every_claim_controlled_catalog_model_inherits_base() -> None:
    models = _claim_controlled_catalog_models()
    assert models, "expected at least one claim-controlled catalog model"
    for model in models:
        assert issubclass(model, ClaimControlledModel), (
            f"{model.__name__} is claim-controlled but does not inherit "
            f"ClaimControlledModel"
        )


def test_every_claim_controlled_catalog_model_has_claims_relation() -> None:
    for model in _claim_controlled_catalog_models():
        field = model._meta.get_field("claims")
        assert field.related_model is Claim, (
            f"{model.__name__}.claims should target Claim, got {field.related_model!r}"
        )
