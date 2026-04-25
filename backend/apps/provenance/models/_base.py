"""Abstract base for entities whose display fields are claim-controlled."""

from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

__all__ = ["ClaimControlledModel"]


class ClaimControlledModel(models.Model):
    """Abstract base for entities whose display fields are claim-controlled.

    Declares the reverse-accessor to provenance claims and the typed ``slug``
    / ``name`` shape that claim-resolver helpers read generically.  Does NOT
    imply URL-addressability, globally-unique slugs, or status tracking —
    those are ``LinkableModel`` / ``SluggedModel`` / ``EntityStatusMixin``
    concerns and are layered in independently at the concrete class.
    """

    # Instance-level annotations let ``type[ClaimControlledModel]`` code read
    # ``.slug`` / ``.name`` without casting.  Concrete subclasses declare the
    # actual CharField / SlugField with their own max_length and validators.
    slug: str
    name: str

    claims = GenericRelation("provenance.Claim")

    class Meta:
        abstract = True
