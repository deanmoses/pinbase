"""Typing protocols for dynamic provenance query shapes."""

from __future__ import annotations

from typing import Protocol


class HasEffectivePriority(Protocol):
    effective_priority: int
