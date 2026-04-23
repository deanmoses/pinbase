"""Typing protocols for dynamic catalog API query shapes."""

from __future__ import annotations

from typing import Protocol


class HasModelCount(Protocol):
    model_count: int


class HasYearRange(Protocol):
    year_min: int | None
    year_max: int | None


class HasTitleCount(Protocol):
    title_count: int


class HasCreditCount(Protocol):
    credit_count: int
