"""API schemas for the citation app."""

from __future__ import annotations

from ninja import Schema
from pydantic import field_validator

NONNULLABLE_STR_FIELDS = (
    "name",
    "source_type",
    "author",
    "publisher",
    "date_note",
    "description",
)


class CitationSourceSearchSchema(Schema):
    id: int
    name: str
    source_type: str
    author: str
    publisher: str
    year: int | None = None
    isbn: str | None = None
    parent_id: int | None = None
    has_children: bool = False
    is_abstract: bool = False
    skip_locator: bool = False
    identifier_key: str = ""


class CitationSourceMatchSchema(Schema):
    id: int
    name: str
    skip_locator: bool = False


class CitationSourceParentSchema(Schema):
    id: int
    name: str


class CitationRecognitionSchema(Schema):
    """A URL or ISBN typed into citation search was recognized as belonging
    to a known parent source. ``child`` is set when a record with the
    extracted ``identifier`` already exists; otherwise the UI has enough to
    prefill a create form.
    """

    parent: CitationSourceParentSchema
    child: CitationSourceMatchSchema | None = None
    identifier: str | None = None


class CitationSourceSearchResponseSchema(Schema):
    results: list[CitationSourceSearchSchema]
    recognition: CitationRecognitionSchema | None = None


class CitationSourceCreateSchema(Schema):
    name: str
    source_type: str
    author: str = ""
    publisher: str = ""
    year: int | None = None
    month: int | None = None
    day: int | None = None
    date_note: str = ""
    isbn: str | None = None
    description: str = ""
    parent_id: int | None = None
    identifier: str = ""
    # Optional: atomically create a CitationSourceLink alongside the source.
    url: str | None = None
    link_label: str = ""
    link_type: str = "homepage"

    @field_validator("isbn", mode="before")
    @classmethod
    def coerce_empty_isbn_to_none(cls, v: object) -> object:
        """Empty string → None for nullable unique field."""
        return None if v == "" else v


class CitationSourceUpdateSchema(Schema):
    name: str | None = None
    source_type: str | None = None
    author: str | None = None
    publisher: str | None = None
    year: int | None = None
    month: int | None = None
    day: int | None = None
    date_note: str | None = None
    isbn: str | None = None
    description: str | None = None

    @field_validator(*NONNULLABLE_STR_FIELDS, mode="before")
    @classmethod
    def coerce_null_to_empty(cls, v: object) -> object:
        """None → empty string for non-nullable CharFields."""
        return "" if v is None else v

    @field_validator("isbn", mode="before")
    @classmethod
    def coerce_empty_isbn_to_none(cls, v: object) -> object:
        """Empty string → None for nullable unique field."""
        return None if v == "" else v


class CitationSourceChildSchema(Schema):
    id: int
    name: str
    source_type: str
    year: int | None = None
    isbn: str | None = None
    skip_locator: bool = False
    urls: list[str] = []


class CitationSourceLinkSchema(Schema):
    id: int
    link_type: str
    url: str
    label: str


class CitationSourceDetailSchema(Schema):
    id: int
    name: str
    source_type: str
    author: str
    publisher: str
    year: int | None = None
    month: int | None = None
    day: int | None = None
    date_note: str
    isbn: str | None = None
    description: str
    identifier_key: str = ""
    skip_locator: bool = False
    parent: CitationSourceParentSchema | None = None
    links: list[CitationSourceLinkSchema] = []
    children: list[CitationSourceChildSchema] = []
    created_at: str
    updated_at: str


class CitationSourceLinkCreateSchema(Schema):
    link_type: str
    url: str
    label: str = ""


class CitationSourceLinkUpdateSchema(Schema):
    link_type: str | None = None
    url: str | None = None
    label: str | None = None

    @field_validator("label", mode="before")
    @classmethod
    def coerce_null_to_empty(cls, v: object) -> object:
        return "" if v is None else v


class CitationExtractInputSchema(Schema):
    input: str


class CitationExtractDraftSchema(Schema):
    name: str
    source_type: str
    author: str
    publisher: str
    year: int | None = None
    isbn: str | None = None
    url: str | None = None


class CitationExtractResultSchema(Schema):
    """Result of looking up a pasted URL/ISBN via an external API.
    ``match`` points at an existing source if one was found; ``draft`` is a
    prefill for the create form; ``error`` is a user-facing failure reason.
    """

    draft: CitationExtractDraftSchema | None = None
    match: CitationSourceMatchSchema | None = None
    error: str | None = None
    confidence: str = ""
    source_api: str = ""
