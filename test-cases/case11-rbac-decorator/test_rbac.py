import pytest

from rbac import AccessDenied, CurrentUser, require_roles


@require_roles("admin")
def _protected(current_user):
    return "ok"


def test_allows_user_with_required_role():
    user = CurrentUser(user_id="u1", roles=["admin"])
    assert _protected(user) == "ok"


def test_denies_user_without_required_role():
    user = CurrentUser(user_id="u2", roles=["support"])
    with pytest.raises(AccessDenied):
        _protected(user)


def test_denies_user_with_no_roles():
    user = CurrentUser(user_id="u3", roles=[])
    with pytest.raises(AccessDenied):
        _protected(user)
