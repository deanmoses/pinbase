"""Auth status API endpoint."""

from __future__ import annotations

from typing import Optional

from ninja import Router, Schema

auth_router = Router(tags=["auth"])


class AuthStatusSchema(Schema):
    is_authenticated: bool
    id: Optional[int] = None
    username: Optional[str] = None


@auth_router.get("/me/", response=AuthStatusSchema)
def auth_me(request):
    """Return current session's authentication state.

    Always succeeds (no auth required). Returns is_authenticated=False for
    anonymous users.
    """
    if request.user.is_authenticated:
        return {
            "is_authenticated": True,
            "id": request.user.id,
            "username": request.user.username,
        }
    return {"is_authenticated": False}
