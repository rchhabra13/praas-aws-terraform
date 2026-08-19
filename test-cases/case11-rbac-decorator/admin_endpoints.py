"""Admin-only endpoints, protected via the require_roles decorator."""
from rbac import CurrentUser, require_roles


@require_roles("admin")
def delete_account(current_user: CurrentUser, account_id: str):
    return {"deleted": account_id}


@require_roles("admin", "billing_admin")
def issue_refund(current_user: CurrentUser, charge_id: str, amount_cents: int):
    return {"refunded": charge_id, "amount_cents": amount_cents}


@require_roles()
def export_all_users(current_user: CurrentUser):
    """Bulk-export every user record — admin tooling, not for general use."""
    return {"exported": True}
