"""Helpers for reader-facing cited edit evidence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TypedDict

from .helpers import citation_instances
from .models import Claim


class EvidenceLink(TypedDict):
    url: str
    label: str


class CitedCitation(TypedDict):
    source_name: str
    source_type: str
    author: str
    year: int | None
    locator: str
    links: list[EvidenceLink]


class CitedChangeset(TypedDict):
    id: int
    user_display: str | None
    note: str
    created_at: str
    fields: list[str]
    citations: list[CitedCitation]


@dataclass
class _CitedChangesetBuilder:
    """Mutable scratch state while grouping citations per changeset."""

    id: int
    user_display: str | None
    note: str
    created_at: str
    fields: list[str] = field(default_factory=list)
    field_set: set[str] = field(default_factory=set)
    citations: dict[tuple[int, str], CitedCitation] = field(default_factory=dict)


def build_cited_changesets(claims: Iterable[Claim]) -> list[CitedChangeset]:
    """Serialize active user changesets that have attached citation instances."""
    grouped: dict[int, _CitedChangesetBuilder] = {}

    for claim in claims:
        if claim.changeset_id is None or claim.user_id is None:
            continue

        claim_citations = citation_instances(claim)
        if not claim_citations:
            continue

        entry = grouped.get(claim.changeset_id)
        if entry is None:
            entry = _CitedChangesetBuilder(
                id=claim.changeset_id,
                user_display=claim.user.username if claim.user else None,
                note=claim.changeset.note if claim.changeset else "",
                created_at=(
                    claim.changeset.created_at.isoformat() if claim.changeset else ""
                ),
            )
            grouped[claim.changeset_id] = entry

        if claim.field_name not in entry.field_set:
            entry.field_set.add(claim.field_name)
            entry.fields.append(claim.field_name)

        for citation in claim_citations:
            signature = (citation.citation_source_id, citation.locator)
            if signature in entry.citations:
                continue
            entry.citations[signature] = {
                "source_name": citation.citation_source.name,
                "source_type": citation.citation_source.source_type,
                "author": citation.citation_source.author,
                "year": citation.citation_source.year,
                "locator": citation.locator,
                "links": [
                    {"url": link.url, "label": link.label}
                    for link in citation.citation_source.links.all()
                ],
            }

    result: list[CitedChangeset] = [
        {
            "id": entry.id,
            "user_display": entry.user_display,
            "note": entry.note,
            "created_at": entry.created_at,
            "fields": entry.fields,
            "citations": list(entry.citations.values()),
        }
        for entry in grouped.values()
    ]
    result.sort(key=lambda item: item["created_at"], reverse=True)
    return result
