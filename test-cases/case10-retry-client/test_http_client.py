from unittest.mock import MagicMock, patch

import requests

from http_client import ResilientClient


def _ok_response():
    resp = MagicMock(spec=requests.Response)
    resp.raise_for_status.return_value = None
    return resp


@patch("http_client.requests.request")
def test_get_retries_on_failure_then_succeeds(mock_request):
    mock_request.side_effect = [requests.ConnectionError("boom"), _ok_response()]
    client = ResilientClient(base_url="https://example.com", max_retries=3)

    response = client.request("GET", "/things/1")

    assert mock_request.call_count == 2
    assert response is not None


@patch("http_client.requests.request")
def test_get_response_is_cached(mock_request):
    mock_request.return_value = _ok_response()
    client = ResilientClient(base_url="https://example.com", cache_ttl_seconds=60)

    first = client.request("GET", "/things/1")
    second = client.request("GET", "/things/1")

    assert mock_request.call_count == 1
    assert first is second


@patch("http_client.requests.request")
def test_raises_after_exhausting_retries(mock_request):
    mock_request.side_effect = requests.ConnectionError("still down")
    client = ResilientClient(base_url="https://example.com", max_retries=2)

    try:
        client.request("GET", "/things/1")
        assert False, "expected ConnectionError"
    except requests.ConnectionError:
        pass

    assert mock_request.call_count == 2
