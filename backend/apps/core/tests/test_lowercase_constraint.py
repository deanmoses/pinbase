"""Regression tests for ``field_lowercase()`` / ``slug_lowercase()``.

Issue #357: the helpers previously emitted ``__regex`` constraints, which
Django translates to ``REGEXP`` SQL on SQLite. ``REGEXP`` depends on a
Python function that Django registers when it opens a connection, so
anything opening the DB outside Django (DB browsers, raw ``sqlite3``
CLI, backup restores via ``sqlite3 < dump.sql``) either fails with
``no such function: regexp`` or silently skips the CHECK.

The fix uses ``field = LOWER(field)`` — pure SQL, portable across every
engine, no UDF setup required.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from django.db import connection
from django.db.models import CheckConstraint, Q
from django.db.models.functions import Lower

from apps.core.models import License, field_lowercase, slug_lowercase


class TestHelperEmitsLowerNotRegex:
    """``field_lowercase()`` and ``slug_lowercase()`` build a ``Lower``-based CHECK."""

    def test_slug_lowercase_uses_lower_function(self):
        constraint = slug_lowercase()
        assert isinstance(constraint, CheckConstraint)
        assert constraint.condition == Q(slug=Lower("slug"))

    def test_field_lowercase_uses_lower_function(self):
        constraint = field_lowercase("location_path")
        assert isinstance(constraint, CheckConstraint)
        assert constraint.condition == Q(location_path=Lower("location_path"))


class TestVanillaSqliteEnforcesCheck:
    """The CHECK fires through a ``sqlite3`` connection that has no Django setup.

    A vanilla connection never registers Django's ``REGEXP`` UDF, so any
    leftover regex-based CHECK would either error with
    ``no such function: regexp`` or silently pass. Lower()-based CHECKs
    fire correctly because they use only built-in SQL.
    """

    def test_uppercase_slug_rejected_in_vanilla_sqlite(self, tmp_path: Path) -> None:
        # Mirror the SQL Django generates for ``Q(slug=Lower("slug"))``.
        # See ``apps/core/migrations/0002_*`` and the live ``core_license``
        # schema: the constraint compiles to ``CHECK ("slug" = (LOWER("slug")))``.
        db_path = tmp_path / "probe.sqlite3"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "CREATE TABLE probe ("
                "  id INTEGER PRIMARY KEY, "
                "  slug TEXT NOT NULL, "
                "  CONSTRAINT probe_slug_lowercase "
                '  CHECK ("slug" = (LOWER("slug")))'
                ")"
            )
            # Lowercase is accepted.
            conn.execute('INSERT INTO probe (slug) VALUES ("ok-slug")')
            # Uppercase fires the CHECK — without any REGEXP UDF in scope.
            with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
                conn.execute('INSERT INTO probe (slug) VALUES ("BadSlug")')
        finally:
            conn.close()

    @pytest.mark.django_db
    def test_no_regexp_in_generated_check_sql(self):
        """Django's emitted schema for a Lower()-based CHECK uses ``LOWER``, not ``REGEXP``.

        Locks in the SQL shape so a future change can't silently revert
        the helper to a regex form without this test failing.
        """
        if connection.vendor != "sqlite":
            pytest.skip("Constraint shape is verified against SQLite SQL output.")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='core_license'"
            )
            row = cursor.fetchone()
        assert row is not None, "core_license table should exist"
        table_sql = row[0].upper()
        assert "REGEXP" not in table_sql
        assert 'CONSTRAINT "CORE_LICENSE_SLUG_LOWERCASE" CHECK ' in table_sql
        assert 'LOWER("SLUG")' in table_sql


@pytest.mark.django_db
class TestDjangoOrmEnforcesCheck:
    """Sanity check: regular Django writes still respect the CHECK."""

    def test_lowercase_slug_accepted(self):
        License.objects.create(
            name="Test License",
            slug="test-license",
            short_name="Test",
        )
        assert License.objects.filter(slug="test-license").exists()

    def test_uppercase_slug_rejected(self):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            License.objects.create(
                name="Bad License",
                slug="Bad-License",
                short_name="Bad",
            )
