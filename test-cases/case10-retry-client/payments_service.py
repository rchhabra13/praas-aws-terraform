"""Thin wrapper around the payments API using the resilient HTTP client."""
from http_client import ResilientClient

_client = ResilientClient(base_url="https://payments.internal.example.com")


def charge_customer(customer_id: str, amount_cents: int) -> dict:
    """Charge a customer and return the resulting charge record."""
    response = _client.request(
        "POST",
        "/v1/charges",
        json={"customer_id": customer_id, "amount_cents": amount_cents},
    )
    return response.json()


def get_customer(customer_id: str) -> dict:
    response = _client.request("GET", f"/v1/customers/{customer_id}")
    return response.json()
