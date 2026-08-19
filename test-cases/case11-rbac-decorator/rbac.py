"""Role-based access control decorator for internal admin endpoints."""
import functools
from typing import Callable


class AccessDenied(Exception):
    pass


class CurrentUser:
    """Placeholder for a request-scoped current-user lookup (e.g. from session/JWT)."""

    def __init__(self, user_id: str, roles: list[str]):
        self.user_id = user_id
        self.roles = roles


def require_roles(*required_roles: str):
    """Restrict a handler to callers who have at least one of `required_roles`.

    Usage:
        @require_roles("admin", "billing_admin")
        def delete_account(current_user, account_id): ...
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(current_user: CurrentUser, *args, **kwargs):
            if required_roles and not any(role in current_user.roles for role in required_roles):
                raise AccessDenied(
                    f"user {current_user.user_id} lacks required roles {required_roles}"
                )
            return func(current_user, *args, **kwargs)

        return wrapper

    return decorator
