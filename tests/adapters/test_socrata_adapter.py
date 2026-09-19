"""Tests for socrata adapter.

This module verifies the documented contracts and edge cases of the socrata adapter
component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

from datetime import datetime, timezone
import json
from unittest.mock import patch

import pytest
import requests

from dp_activity.adapters.socrata_adapter import SocrataAdapter

ENDPOINT = "https://example.test/resource/6933-unw5.json"
JSON_HEADERS = {"Content-Type": "application/json"}


def test_download_materializes_records_and_metadata(monkeypatch) -> None:
    """Verify that download materializes records and metadata.

    Args:
        monkeypatch: Pytest fixture used to replace behavior during the test.
    """
    adapter = SocrataAdapter("https://example.test/resource/6933-unw5.json")
    rows = [{"permitnum": "DP1"}, {"permitnum": "DP2"}]
    monkeypatch.setattr(adapter, "iter_records", lambda **query: iter(rows))

    started = datetime.now(timezone.utc)
    downloaded, metadata = adapter.download(where="applieddate is not null")

    assert downloaded == rows
    assert metadata.row_count == 2
    assert metadata.dataset_id == "6933-unw5"
    assert metadata.endpoint == ENDPOINT
    assert started <= metadata.retrieved_at_utc <= datetime.now(timezone.utc)
    assert metadata.retrieved_at_utc.tzinfo == timezone.utc
    assert json.loads(metadata.query) == {"where": "applieddate is not null"}


def test_pagination_preserves_records_and_query(requests_mock) -> None:
    """Keep filtering and authentication consistent across page boundaries.

    Args:
        requests_mock: Fixture intercepting HTTP requests without network access.
    """
    rows = [{"permitnum": "DP1"}, {"permitnum": "DP2"}, {"permitnum": "DP3"}]
    requests_mock.get(ENDPOINT, [
        {"json": rows[:2], "headers": JSON_HEADERS},
        {"json": rows[2:], "headers": JSON_HEADERS},
    ])
    adapter = SocrataAdapter(ENDPOINT, app_token="test-token")

    records, metadata = adapter.download(
        select="permitnum", where="permitnum IS NOT NULL", page_size=2
    )

    assert records == rows
    assert metadata.row_count == 3
    assert "test-token" not in metadata.query
    assert len(requests_mock.request_history) == 2
    for offset, request in zip((0, 2), requests_mock.request_history):
        assert request.qs == {
            "$limit": ["2"], "$offset": [str(offset)], "$order": [":id"],
            "$select": ["permitnum"], "$where": ["permitnum is not null"],
        }
        assert request.headers["X-App-Token"] == "test-token"
        assert request.headers["Accept"] == "application/json"
        assert request.timeout == 30


@pytest.mark.parametrize("rows", [[], [{"permitnum": "DP1"}]])
def test_empty_page_terminates_download(requests_mock, rows) -> None:
    """Stop at an empty page for empty sources and exact page multiples.

    Args:
        requests_mock: Fixture intercepting HTTP requests.
        rows: Initial page, empty or exactly one requested page.
    """
    requests_mock.get(ENDPOINT, [
        {"json": rows, "headers": JSON_HEADERS},
        {"json": [], "headers": JSON_HEADERS},
    ])
    records, metadata = SocrataAdapter(ENDPOINT).download(page_size=1)
    assert records == rows
    assert metadata.row_count == len(rows)
    assert requests_mock.call_count == (2 if rows else 1)
    assert "X-App-Token" not in requests_mock.last_request.headers


@pytest.mark.parametrize("page_size", [0, -1, True, 1.5, "10", None])
def test_invalid_page_size_fails_before_request(requests_mock, page_size) -> None:
    """Reject sizes that cannot advance pagination predictably.

    Args:
        requests_mock: Fixture recording any unexpected HTTP request.
        page_size: Invalid size supplied by a caller.
    """
    with pytest.raises(ValueError, match="positive integer"):
        list(SocrataAdapter(ENDPOINT).iter_records(page_size=page_size))
    assert not requests_mock.called


@pytest.mark.parametrize("query", [{"select": " "}, {"where": 1}, {"where": ""}])
def test_invalid_expressions_fail_before_request(requests_mock, query) -> None:
    """Reject malformed option types without contacting the source.

    Args:
        requests_mock: Fixture recording unexpected HTTP requests.
        query: Invalid selection or filter options.
    """
    with pytest.raises(ValueError, match="nonblank string"):
        SocrataAdapter(ENDPOINT).download(**query)
    assert not requests_mock.called


@pytest.mark.parametrize("payload", [{"error": "bad query"}, [1], [None], None])
def test_invalid_response_shape_is_rejected(requests_mock, payload) -> None:
    """Prevent malformed API results from entering the analytical core.

    Args:
        requests_mock: Fixture supplying the HTTP response.
        payload: JSON value violating the list-of-records contract.
    """
    requests_mock.get(ENDPOINT, text=json.dumps(payload), headers=JSON_HEADERS)
    with pytest.raises(ValueError, match="list of objects"):
        SocrataAdapter(ENDPOINT).download()
    assert requests_mock.call_count == 1


def test_invalid_json_is_not_retried(requests_mock) -> None:
    """Report invalid JSON rather than masking it as a transient outage.

    Args:
        requests_mock: Fixture supplying an invalid JSON response.
    """
    requests_mock.get(
        ENDPOINT, text="<html>not JSON</html>", headers=JSON_HEADERS
    )
    with pytest.raises(ValueError, match="not valid JSON"):
        SocrataAdapter(ENDPOINT).download()
    assert requests_mock.call_count == 1


def test_repeated_pages_fail_before_duplicate_records_are_yielded(requests_mock) -> None:
    """Detect pagination cycles even when the repeat is not consecutive.

    Args:
        requests_mock: Fixture supplying a cycle of pages.
    """
    requests_mock.get(ENDPOINT, [
        {"json": [{"permitnum": "DP1"}], "headers": JSON_HEADERS},
        {"json": [{"permitnum": "DP2"}], "headers": JSON_HEADERS},
        {"json": [{"permitnum": "DP1"}], "headers": JSON_HEADERS},
    ])
    records = SocrataAdapter(ENDPOINT).iter_records(page_size=1)
    assert next(records) == {"permitnum": "DP1"}
    assert next(records) == {"permitnum": "DP2"}
    with pytest.raises(RuntimeError, match="repeated page"):
        next(records)


@pytest.mark.parametrize("failure", [
    {"status_code": status} for status in (429, 500, 502, 503, 504)
] + [{"exc": requests.ConnectionError}, {"exc": requests.Timeout}])
def test_transient_failures_retry_same_page(requests_mock, monkeypatch, failure) -> None:
    """Recover without skipping records or retrying indefinitely.

    Args:
        requests_mock: Fixture supplying transient failures and recovery.
        monkeypatch: Fixture replacing retry delays.
        failure: HTTP or transport failure to recover from.
    """
    delays = []
    monkeypatch.setattr("dp_activity.adapters.socrata_adapter.sleep", delays.append)
    requests_mock.get(ENDPOINT, [
        failure, failure, {"json": [{"permitnum": "DP1"}], "headers": JSON_HEADERS}
    ])
    records, _ = SocrataAdapter(ENDPOINT).download()
    assert records == [{"permitnum": "DP1"}]
    assert delays == [1, 2]
    assert requests_mock.call_count == 3
    assert all(request.qs["$offset"] == ["0"] for request in requests_mock.request_history)


@pytest.mark.parametrize("failure, expected, attempts", [
    ({"status_code": 400}, requests.HTTPError, 1),
    ({"status_code": 401}, requests.HTTPError, 1),
    ({"status_code": 404}, requests.HTTPError, 1),
    ({"status_code": 503}, requests.HTTPError, 3),
    ({"exc": requests.Timeout}, requests.Timeout, 3),
    ({"exc": requests.ConnectionError}, requests.ConnectionError, 3),
])
def test_failures_propagate_with_bounded_attempts(
    requests_mock, monkeypatch, failure, expected, attempts
) -> None:
    """Propagate permanent or exhausted failures instead of partial success.

    Args:
        requests_mock: Fixture supplying a persistent failure.
        monkeypatch: Fixture replacing retry delays.
        failure: HTTP response or exception representing the failure.
        expected: Exception type expected by the caller.
        attempts: Maximum expected number of requests.
    """
    delays = []
    monkeypatch.setattr("dp_activity.adapters.socrata_adapter.sleep", delays.append)
    requests_mock.get(ENDPOINT, **failure)
    with pytest.raises(expected):
        SocrataAdapter(ENDPOINT).download()
    assert requests_mock.call_count == attempts
    assert delays == ([1, 2] if attempts == 3 else [])


@pytest.mark.parametrize("endpoint", [
    "not-a-url", "https://example.test/resource/6933-unw5.csv",
    ENDPOINT + "?$limit=1", ENDPOINT + "#fragment",
    "https://user:password@example.test/resource/6933-unw5.json",
])
def test_invalid_endpoint_is_rejected(endpoint) -> None:
    """Keep endpoint metadata unambiguous and credentials out of URLs.

    Args:
        endpoint: URL that does not meet the adapter's resource contract.
    """
    with pytest.raises(ValueError, match="Socrata JSON resource URL"):
        SocrataAdapter(endpoint)


def test_default_query_metadata_is_none(requests_mock) -> None:
    """Represent an unfiltered empty download without fabricated query text.

    Args:
        requests_mock: Fixture supplying an empty dataset.
    """
    requests_mock.get(ENDPOINT, json=[], headers=JSON_HEADERS)
    records, metadata = SocrataAdapter(ENDPOINT).download()
    assert records == []
    assert metadata.query is None


@pytest.mark.parametrize("endpoint", [ENDPOINT, "http://example.test:8080/resource/6933-unw5.json"])
def test_sodapy_preserves_endpoint_scheme_and_port(requests_mock, endpoint) -> None:
    """Translate complete endpoint URLs to the client's domain-based interface.

    Args:
        requests_mock: Fixture intercepting the exact target URL.
        endpoint: Supported URL whose scheme and authority must be preserved.
    """
    requests_mock.get(endpoint, json=[], headers=JSON_HEADERS)
    _, metadata = SocrataAdapter(endpoint).download()
    assert requests_mock.call_count == 1
    assert metadata.endpoint == endpoint


@pytest.mark.parametrize("invalid_page", [False, True])
def test_sodapy_session_closes_on_completion_or_error(requests_mock, invalid_page) -> None:
    """Release the third-party client's connection pool on success and failure.

    Args:
        requests_mock: Fixture supplying a valid or invalid response.
        invalid_page: Whether to trigger response validation failure.
    """
    requests_mock.get(ENDPOINT, json={} if invalid_page else [], headers=JSON_HEADERS)
    with patch.object(requests.Session, "close", autospec=True) as close:
        if invalid_page:
            with pytest.raises(ValueError, match="list of objects"):
                SocrataAdapter(ENDPOINT).download()
        else:
            SocrataAdapter(ENDPOINT).download()
        close.assert_called_once()


def test_sodapy_session_closes_when_iteration_is_stopped(requests_mock) -> None:
    """Allow callers to release connections after consuming only part of a page.

    Args:
        requests_mock: Fixture supplying a page that will be partially consumed.
    """
    requests_mock.get(
        ENDPOINT, json=[{"permitnum": "DP1"}, {"permitnum": "DP2"}], headers=JSON_HEADERS
    )
    with patch.object(requests.Session, "close", autospec=True) as close:
        records = SocrataAdapter(ENDPOINT).iter_records(page_size=2)
        assert next(records) == {"permitnum": "DP1"}
        records.close()
        close.assert_called_once()
