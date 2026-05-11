"""Wire-format schemas for policy-denial responses.

``PolicyDeniedSchema`` is the structured 403 body produced by
:class:`apps.core.authz.exceptions.PolicyDeniedError`. Routes that can emit
both a policy denial and a non-policy plain-string 403 declare the
union ``PolicyDeniedSchema | ErrorDetailSchema`` so Ninja serializes
each per actual body shape.
"""

from __future__ import annotations

from typing import Any, Literal

from ninja import Schema

from apps.core.schemas import StructuredErrorBodySchema


class PolicyDeniedBodySchema(StructuredErrorBodySchema):
    kind: Literal["policy_denied"]
    code: str
    context: dict[str, Any]


class PolicyDeniedSchema(Schema):
    """Structured 403 body produced by ``PolicyDeniedError``."""

    detail: PolicyDeniedBodySchema
