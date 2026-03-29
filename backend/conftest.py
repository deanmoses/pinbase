import pytest

from apps.catalog.models import CreditRole, Person


@pytest.fixture
def credit_targets(db):
    """Seed Person + CreditRole rows commonly referenced by credit claim tests.

    Relationship claim validation checks target existence at the claim
    boundary, so any test that creates credit claims needs the referenced
    Person and CreditRole rows to exist.
    """
    Person.objects.bulk_create(
        [
            Person(name="Pat Lawlor", slug="pat-lawlor"),
            Person(name="John Youssi", slug="john-youssi"),
        ],
        update_conflicts=True,
        unique_fields=["slug"],
        update_fields=["name"],
    )
    CreditRole.objects.bulk_create(
        [
            CreditRole(name="Design", slug="design"),
            CreditRole(name="Art", slug="art"),
        ],
        update_conflicts=True,
        unique_fields=["slug"],
        update_fields=["name"],
    )


@pytest.fixture(autouse=True)
def _use_locmem_cache(settings):
    """Use in-memory cache for tests instead of file-based cache.

    File-based cache persists across test boundaries and causes flaky
    failures when other tests call invalidate_all() during their execution.
    """
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture(autouse=True)
def _default_display_policy_show_all(settings):
    """Default Constance display policy to show-all for tests.

    Most tests don't care about license filtering. Tests that specifically
    test threshold behavior can override via settings fixture.
    """
    from constance.test import override_config

    with override_config(CONTENT_DISPLAY_POLICY="show-all"):
        yield
