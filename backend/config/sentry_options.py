"""Sentry options assembled outside ``settings.py`` for testability.

The ``ignore_errors`` list is the in-code half of
ObservabilityArchitecture.md § Capture scope's "don't capture"
contract. Pulling it out of ``settings.py`` lets tests import the
same list rather than redeclare it (which would silently drift).

These imports are cheap — every name here is already loaded by the
Django app at startup. The reason ``settings.py`` gates Sentry
imports is the ``sentry_sdk`` package itself; nothing in this
module touches it.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from ninja.errors import ValidationError as NinjaValidationError

from apps.core.exceptions import StructuredApiError

# ``DjangoIntegration`` hooks ``got_request_exception``, which fires
# for these classes before Django's exception handler maps them to a
# 4xx response. Without this filter they'd flood the issue stream.
# ``StructuredApiError`` covers rate-limit denials and other
# structured 4xx errors raised through Ninja.
#
# Including ``StructuredApiError`` as a base class is load-bearing on
# a convention: **every subclass must be 4xx**. Sentry's
# ``ignore_errors`` matches by ``isinstance``, so a 5xx subclass
# (e.g. a future ``StructuredServerError``) would silently disappear
# from the issue stream. ``test_all_structured_api_error_subclasses_are_4xx``
# in ``test_sentry_ignore_errors.py`` is the CI-grade regression guard.
IGNORE_ERRORS: list[type[BaseException]] = [
    ValidationError,
    NinjaValidationError,
    PermissionDenied,
    Http404,
    StructuredApiError,
]
