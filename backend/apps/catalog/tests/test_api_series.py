"""Query-count regression for the series list endpoint.

The `list_series` view uses a ``Prefetch("titles__machine_models", ...)``
whose inner queryset narrows columns via ``.only(...)``. If the FK
back-pointer (``title_id``) is omitted from ``.only(...)``, Django's
prefetch machinery does a ``refresh_from_db`` per prefetched row to
recover the column it needs to wire up the parent association, scaling
queries linearly with the number of MachineModels in the response.
"""

from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog.models import Series, Title
from apps.catalog.tests.conftest import make_machine_model


def _seed(start: int, count: int) -> None:
    for i in range(start, start + count):
        series = Series.objects.create(name=f"Series {i}", slug=f"series-{i}")
        title = Title.objects.create(
            name=f"Title {i}", slug=f"title-{i}", series=series
        )
        make_machine_model(title=title, name=f"Machine {i}", slug=f"machine-{i}")


@pytest.mark.django_db
def test_list_series_query_count_does_not_scale_with_rows(client):
    """Adding more rows to the response must not add queries."""
    _seed(start=0, count=2)
    with CaptureQueriesContext(connection) as small_ctx:
        resp = client.get("/api/series/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2
    small_count = len(small_ctx.captured_queries)

    _seed(start=2, count=8)

    with CaptureQueriesContext(connection) as big_ctx:
        resp = client.get("/api/series/")
        assert resp.status_code == 200
        assert len(resp.json()) == 10
    big_count = len(big_ctx.captured_queries)

    assert big_count == small_count, (
        f"Query count scaled with row count: {small_count} queries at N=2, "
        f"{big_count} at N=10. Likely a refresh_from_db-per-row caused by "
        f"a Prefetch().only(...) that omits the FK back-pointer.\n"
        f"Extra queries:\n"
        + "\n".join(q["sql"] for q in big_ctx.captured_queries[small_count:])
    )
