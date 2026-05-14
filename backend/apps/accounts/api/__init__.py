"""Auth & user API endpoint aggregator.

Endpoints live in `apps.accounts.api.{auth,signup,profile}`; this package
composes their routers into the `routers` list consumed by Ninja URL
discovery.
"""

from __future__ import annotations

from .auth import auth_router
from .profile import user_page_router
from .signup import signup_router

routers = [
    ("/auth/", auth_router),
    ("/auth/signup/", signup_router),
    ("/pages/user/", user_page_router),
]
