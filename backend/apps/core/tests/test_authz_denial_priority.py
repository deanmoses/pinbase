"""Asserts the DENIAL_PRIORITY tuple covers every DenialCode.

The evaluator falls back to "sort last" for codes not in
`DENIAL_PRIORITY`. That fallback is fine for forward-compatibility
during a deploy, but it would let a new `DenialCode` member silently
sort last forever if nobody updated the priority list. This test
keeps the fallback dead.
"""

from __future__ import annotations

from apps.core.authz.types import DENIAL_PRIORITY, DenialCode


def test_denial_priority_covers_every_code():
    assert set(DENIAL_PRIORITY) == set(DenialCode), (
        "DENIAL_PRIORITY must list every DenialCode. Missing: "
        f"{set(DenialCode) - set(DENIAL_PRIORITY)!r}; "
        f"extra: {set(DENIAL_PRIORITY) - set(DenialCode)!r}."
    )


def test_denial_priority_has_no_duplicates():
    assert len(DENIAL_PRIORITY) == len(set(DENIAL_PRIORITY))
