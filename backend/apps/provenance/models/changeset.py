"""ChangeSet model: grouped edit sessions."""

from __future__ import annotations

from django.conf import settings
from django.db import models


class ChangeSet(models.Model):
    """A grouped edit session that links related claims.

    A ChangeSet is a thin grouping record, not a snapshot of entity state.
    Truth is always derived from claim resolution (highest priority wins).
    Reverting a ChangeSet means creating inverse claims, not restoring a
    snapshot.

    All claims in a ChangeSet must share the same actor (same user or same
    source). This invariant is enforced by the code that creates ChangeSets,
    not by database constraints.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="changesets",
        null=True,
        blank=True,
        help_text="The user who made this edit. Null for future source-level changesets.",
    )
    note = models.TextField(
        blank=True,
        default="",
        help_text="Optional free-text note explaining the edit.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        actor = self.user.username if self.user else "system"
        return f"ChangeSet #{self.pk} by {actor}"
