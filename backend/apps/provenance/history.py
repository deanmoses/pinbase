"""Edit-history helpers for provenance changesets."""

from __future__ import annotations

from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.db.models import Case, F, IntegerField, Model, Prefetch, Q, Value, When

from apps.core.authz import PolicyUser, compute_row_capabilities

from .models import ChangeSet, Claim
from .schemas import (
    ChangeSetAttributionSchema,
    ChangeSetSchema,
    FieldChangeSchema,
    RetractionSchema,
)


def _compute_winning_claim_ids(ct: ContentType, entity_pk: int) -> set[int]:
    """Return the set of claim PKs that are current winners for the entity.

    For each ``claim_key``, the winner is the active claim with the highest
    ``effective_priority``, breaking ties by most recent ``created_at``, then
    highest ``pk``.
    """
    active_claims = (
        Claim.objects.filter(
            content_type=ct,
            object_id=entity_pk,
            is_active=True,
        )
        .exclude(source__is_enabled=False)
        .annotate(
            effective_priority=Case(
                When(source__isnull=False, then=F("source__priority")),
                When(user__isnull=False, then=F("user__priority")),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        .order_by("claim_key", "-effective_priority", "-created_at", "-pk")
    )

    winners: set[int] = set()
    seen_keys: set[str] = set()
    for claim in active_claims:
        if claim.claim_key not in seen_keys:
            seen_keys.add(claim.claim_key)
            winners.add(claim.pk)
    return winners


def build_edit_history(entity: Model, user: PolicyUser) -> list[ChangeSetSchema]:
    """Build changeset-grouped edit history with old→new diffs for an entity.

    Returns ChangeSetSchema rows newest first. Uses two queries to avoid N+1:
    one for changesets with their claims, one for all inactive user claims
    (to look up previous values).

    ``user`` is the caller (boundary-cast via ``policy_user``) and is
    used to populate the per-row ``capabilities`` map.
    """
    ct = ContentType.objects.get_for_model(entity)

    # 1. Fetch changesets that have claims OR retracted_claims for this entity.
    changesets = (
        ChangeSet.objects.filter(
            Q(claims__content_type=ct, claims__object_id=entity.pk)
            | Q(
                retracted_claims__content_type=ct,
                retracted_claims__object_id=entity.pk,
            )
        )
        .distinct()
        .select_related("user", "ingest_run__source")
        .prefetch_related(
            Prefetch(
                "claims",
                queryset=Claim.objects.filter(
                    content_type=ct, object_id=entity.pk
                ).order_by("field_name"),
            ),
            Prefetch(
                "retracted_claims",
                queryset=Claim.objects.filter(
                    content_type=ct, object_id=entity.pk
                ).order_by("field_name"),
            ),
        )
        .order_by("-created_at")
    )

    # 2. Fetch ALL claims for this entity (active + inactive, any author) to
    #    build a per-field history chain for old-value lookups. The "old
    #    value" for a user edit is whatever the field's most recent prior
    #    claim was — be it a previous user edit, ingest, or source.
    all_claims = list(
        Claim.objects.filter(
            content_type=ct,
            object_id=entity.pk,
        ).order_by("claim_key", "-created_at", "-pk")
    )

    # Build lookup: claim_key → list of claims ordered newest-first.
    history: dict[str, list[Claim]] = defaultdict(list)
    for c in all_claims:
        history[c.claim_key].append(c)

    # 3. Compute winning claims for is_winning.
    winning_ids = _compute_winning_claim_ids(ct, entity.pk)

    # 4. Build response.
    result: list[ChangeSetSchema] = []
    for cs in changesets:
        changes: list[FieldChangeSchema] = []
        for claim in cs.claims.all():
            chain = history.get(claim.claim_key, [])
            old_value = None
            for i, c in enumerate(chain):
                if c.pk == claim.pk and i + 1 < len(chain):
                    old_value = chain[i + 1].value
                    break
            changes.append(
                FieldChangeSchema(
                    field_name=claim.field_name,
                    claim_key=claim.claim_key,
                    old_value=old_value,
                    new_value=claim.value,
                    claim_id=claim.pk,
                    claim_user_id=claim.user_id,
                    is_active=claim.is_active,
                    is_winning=claim.pk in winning_ids,
                    is_retracted=claim.retracted_by_changeset_id is not None,
                )
            )

        retractions: list[RetractionSchema] = [
            RetractionSchema(
                claim_id=c.pk,
                field_name=c.field_name,
                claim_key=c.claim_key,
                old_value=c.value,
            )
            for c in cs.retracted_claims.all()
        ]

        assert cs.pk is not None
        result.append(
            ChangeSetSchema(
                id=cs.pk,
                attribution=ChangeSetAttributionSchema(
                    user_username=cs.user.username if cs.user else None,
                    is_ingest=cs.ingest_run_id is not None,
                    source_name=cs.ingest_run.source.name if cs.ingest_run else None,
                    created_at=cs.created_at.isoformat(),
                ),
                note=cs.note,
                changes=changes,
                retractions=retractions,
                capabilities=compute_row_capabilities(
                    user, cs, ChangeSetSchema.policy_activities
                ),
            )
        )
    return result
