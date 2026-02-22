"""Shared base models and utilities used across all apps."""

from __future__ import annotations

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base adding created_at / updated_at timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def unique_slug(obj, source: str, fallback: str = "item") -> str:
    """Generate a unique slug with counter disambiguation.

    Appends a counter suffix (-2, -3, …) until the slug is unique within
    the model's table.
    """
    from django.utils.text import slugify

    base = slugify(source) or fallback
    slug = base
    counter = 2
    while type(obj).objects.filter(slug=slug).exclude(pk=obj.pk).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
