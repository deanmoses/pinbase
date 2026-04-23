"""Typing protocols and named-tuple shapes for catalog API query plumbing."""

from __future__ import annotations

from typing import NamedTuple, Protocol


class HasModelCount(Protocol):
    model_count: int


class HasYearRange(Protocol):
    year_min: int | None
    year_max: int | None


class HasTitleCount(Protocol):
    title_count: int


class HasCreditCount(Protocol):
    credit_count: int


class SlugName(NamedTuple):
    """A (slug, name) pair for a facet ref pulled in bulk from ``values_list``.

    Used throughout list-endpoint assembly where we collect slug+display-name
    pairs per row (tech generations, themes, gameplay features, etc.) without
    the overhead of a full Schema instance.
    """

    slug: str
    name: str


class CreditKey(NamedTuple):
    """A credit identified by (person_slug, role_slug) — the input-side key."""

    person_slug: str
    role_slug: str


class CreditPkKey(NamedTuple):
    """A credit identified by (person_pk, role_pk) — the DB-side key."""

    person_pk: int
    role_pk: int
