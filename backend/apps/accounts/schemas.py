"""Schemas for signup (onboarding) endpoints.

Existing accounts schemas live inline in `api.py` (grandfathered by the
inline-schema baseline in `test_openapi_boundaries.py`). New schemas go
here.

Error bodies mirror the envelope produced by the global
`StructuredApiError` handler in [config/api.py](../../../config/api.py):
`{"detail": {"kind": <kind>, "message": <message>, ...extra}}`. The
`*ErrorBodySchema` classes describe the inner `detail` object; the
`*ErrorSchema` wrappers add the outer `detail:` field for declaration
on the endpoint `response={}` map.
"""

from __future__ import annotations

from typing import Literal

from ninja import Schema
from pydantic import Field

from apps.core.schemas import StructuredErrorBodySchema

from .usernames import UsernameFormatRejectReason, UsernameRejectReason


class SignupPendingResponseSchema(Schema):
    """Identity fields surfaced on the onboarding page header."""

    first_name: str
    last_name: str
    email: str


class SignupCheckResponseSchema(Schema):
    available: bool
    # `taken` and the format/reserved codes both surface here; the format
    # validator never produces `taken`. None when `available=True`.
    reason: UsernameRejectReason | None = None


class SignupSubmitRequestSchema(Schema):
    # Pydantic max_length is intentionally generous (DoS guard only). Do
    # NOT set this to USERNAME_MAX_LEN (20) — that would make Ninja reject
    # oversize submits with a 422 validation error before the handler can
    # emit the typed `too_long` reason via UsernameRejectedError.
    username: str = Field(max_length=200)


class SignupSubmitResponseSchema(Schema):
    redirect_url: str


class SignupCancelResponseSchema(Schema):
    logout_url: str


class PendingInvalidErrorBodySchema(StructuredErrorBodySchema):
    kind: Literal["pending_invalid"]


class PendingInvalidErrorSchema(Schema):
    detail: PendingInvalidErrorBodySchema


class UsernameRejectedErrorBodySchema(StructuredErrorBodySchema):
    kind: Literal["username_rejected"]
    # Narrower than UsernameRejectReason — `taken` is its own kind
    # (UsernameTakenError, 409), never a value here.
    reason: UsernameFormatRejectReason


class UsernameRejectedErrorSchema(Schema):
    detail: UsernameRejectedErrorBodySchema


class UsernameTakenErrorBodySchema(StructuredErrorBodySchema):
    kind: Literal["username_taken"]


class UsernameTakenErrorSchema(Schema):
    detail: UsernameTakenErrorBodySchema
