"""Tests for the frontend SPA catch-all view."""

import re

import pytest
from django.http import Http404
from django.test import Client, RequestFactory, override_settings
from django.urls import re_path

from config.urls import frontend_spa


# ── Integration tests: Django routing is not intercepted ───────────


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_api_health_not_intercepted():
    """GET /api/health should reach Django Ninja, not the catch-all."""
    client = Client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@override_settings(
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
def test_admin_login_not_intercepted():
    """GET /admin/login/ should reach Django Admin, not the catch-all."""
    client = Client()
    response = client.get("/admin/login/")
    assert response.status_code == 200


def test_api_no_trailing_slash_not_intercepted():
    """GET /api should not be caught by the SPA catch-all."""
    client = Client()
    response = client.get("/api")
    # Django's APPEND_SLASH redirects /api → /api/ since the catch-all
    # regex excludes both /api and /api/...
    assert response.status_code in (301, 302)
    assert response["Location"].endswith("/api/")


def test_admin_no_trailing_slash_not_intercepted():
    """GET /admin should not be caught by the SPA catch-all."""
    client = Client()
    response = client.get("/admin")
    assert response.status_code in (200, 301, 302)


# ── URL wiring tests: regex produces correct kwargs ────────────────

# The actual pattern from urls.py (duplicated here so the test breaks if the
# pattern is accidentally changed to something incompatible).
_CATCH_ALL_PATTERN = r"^(?!api(?:/|$)|admin(?:/|$))(?P<path>.*)$"


@pytest.mark.parametrize(
    "url,expected_path",
    [
        ("", ""),
        ("manufacturers/williams", "manufacturers/williams"),
        ("about", "about"),
        ("deep/nested/route", "deep/nested/route"),
    ],
)
def test_catch_all_regex_captures_path(url, expected_path):
    """The catch-all regex should capture the URL as a named 'path' group."""
    m = re.match(_CATCH_ALL_PATTERN, url)
    assert m is not None, f"Pattern did not match '{url}'"
    assert m.group("path") == expected_path
    # No spurious positional groups
    assert all(g is not None for g in m.groups()), (
        f"Regex produced None groups: {m.groups()}"
    )


@pytest.mark.parametrize(
    "url",
    ["api/", "api", "api/health", "admin/", "admin", "admin/login/"],
)
def test_catch_all_regex_excludes_api_admin(url):
    """The catch-all regex should NOT match api/* or admin/* URLs."""
    m = re.match(_CATCH_ALL_PATTERN, url)
    assert m is None, f"Pattern should not match '{url}'"


def test_catch_all_url_resolves_to_frontend_spa(tmp_path):
    """Verify Django URL resolution passes the correct path kwarg to frontend_spa."""
    pattern = re_path(_CATCH_ALL_PATTERN, frontend_spa)
    match = pattern.resolve("manufacturers/williams")
    assert match is not None
    assert match.func is frontend_spa
    assert match.kwargs == {"path": "manufacturers/williams"}


# ── Unit tests: frontend_spa view directly ─────────────────────────


def _make_build_dir(tmp_path, files=None):
    """Create a temporary frontend build directory with given files."""
    build_dir = tmp_path / "frontend_build"
    build_dir.mkdir()
    (build_dir / "index.html").write_text(
        "<!doctype html><html><body>Prerendered homepage</body></html>"
    )
    (build_dir / "200.html").write_text(
        "<!doctype html><html><body>SPA shell</body></html>"
    )
    for relpath, content in (files or {}).items():
        f = build_dir / relpath
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
    return build_dir


def test_spa_route_serves_200_html(tmp_path):
    """A generic SPA route should serve the fallback 200.html."""
    build_dir = _make_build_dir(tmp_path)
    request = RequestFactory().get("/some/spa/route")
    with override_settings(FRONTEND_BUILD_DIR=build_dir):
        response = frontend_spa(request, path="some/spa/route")
    assert response.status_code == 200
    content = response.content.decode()
    assert "SPA shell" in content


def test_prerendered_path_html(tmp_path):
    """A prerendered route with trailingSlash: 'never' should serve path.html."""
    build_dir = _make_build_dir(
        tmp_path, {"about.html": "<html><body>About page</body></html>"}
    )
    request = RequestFactory().get("/about")
    with override_settings(FRONTEND_BUILD_DIR=build_dir):
        response = frontend_spa(request, path="about")
    assert response.status_code == 200
    content = response.content.decode()
    assert "About page" in content


def test_prerendered_index_html(tmp_path):
    """A prerendered route with trailingSlash: 'always' should serve path/index.html."""
    build_dir = _make_build_dir(
        tmp_path,
        {"about/index.html": "<html><body>About dir index</body></html>"},
    )
    request = RequestFactory().get("/about")
    with override_settings(FRONTEND_BUILD_DIR=build_dir):
        response = frontend_spa(request, path="about")
    assert response.status_code == 200
    content = response.content.decode()
    assert "About dir index" in content


def test_path_html_takes_precedence_over_dir_index(tmp_path):
    """path.html should be preferred over path/index.html."""
    build_dir = _make_build_dir(
        tmp_path,
        {
            "about.html": "<html><body>path.html wins</body></html>",
            "about/index.html": "<html><body>index.html loses</body></html>",
        },
    )
    request = RequestFactory().get("/about")
    with override_settings(FRONTEND_BUILD_DIR=build_dir):
        response = frontend_spa(request, path="about")
    content = response.content.decode()
    assert "path.html wins" in content


def test_asset_extension_returns_404(tmp_path):
    """Requests for missing assets (known extensions) should 404, not serve SPA shell."""
    build_dir = _make_build_dir(tmp_path)
    request = RequestFactory().get("/missing-chunk.js")
    with override_settings(FRONTEND_BUILD_DIR=build_dir), pytest.raises(Http404):
        frontend_spa(request, path="missing-chunk.js")


def test_slug_with_dot_serves_spa(tmp_path):
    """Slugs with dots that aren't known asset extensions should serve the SPA shell."""
    build_dir = _make_build_dir(tmp_path)
    request = RequestFactory().get("/manufacturers/acme.co")
    with override_settings(FRONTEND_BUILD_DIR=build_dir):
        response = frontend_spa(request, path="manufacturers/acme.co")
    assert response.status_code == 200
    content = response.content.decode()
    assert "SPA shell" in content


def test_path_traversal_blocked(tmp_path):
    """Path traversal attempts should not escape the build directory."""
    build_dir = _make_build_dir(tmp_path)
    request = RequestFactory().get("/../../etc/passwd")
    with override_settings(FRONTEND_BUILD_DIR=build_dir):
        response = frontend_spa(request, path="../../etc/passwd")
    # Should fall through to SPA shell, not serve a file outside build_dir
    assert response.status_code == 200
    content = response.content.decode()
    assert "SPA shell" in content


def test_root_path_serves_prerendered_index(tmp_path):
    """GET / should serve the prerendered index.html (homepage)."""
    build_dir = _make_build_dir(tmp_path)
    request = RequestFactory().get("/")
    with override_settings(FRONTEND_BUILD_DIR=build_dir):
        response = frontend_spa(request, path="")
    assert response.status_code == 200
    content = response.content.decode()
    assert "Prerendered homepage" in content
