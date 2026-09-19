"""Adapter for the City of Calgary Socrata API.

This module wraps sodapy's Socrata client and owns pagination, validation, retry
policy, and reproducibility metadata so external API details do not leak into
analytical code.

Design Pattern:
    Adapter.

Pattern Rationale:
    SocrataAdapter is an object adapter: it composes a sodapy.Socrata client
    (the adaptee) and translates its get() interface into project-owned record
    iteration and download metadata. The analysis pipeline stays independent of
    the third-party client and its request conventions.

Typical Usage:
    Construct SocrataAdapter with a JSON resource endpoint, then iterate records
    or call download() for records and metadata. Pass the result to a repository
    or file-format adapter for persistence.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from time import sleep
from typing import Any
from urllib.parse import urlsplit

import requests
from sodapy import Socrata


@dataclass(frozen=True)
class DownloadMetadata:
    """Record facts needed to reproduce a source download.

    This immutable value object travels with a raw snapshot so its dataset, endpoint,
    retrieval time, row count, and query remain auditable.

    Attributes:
        dataset_id: Socrata dataset identifier parsed from the endpoint.
        endpoint: Source endpoint used for the request.
        retrieved_at_utc: UTC time at which retrieval completed.
        row_count: Number of materialized source records.
        query: JSON-serialized iterator options supplied to download(), or None
            when no options were supplied. Tokens are never included.
    """

    dataset_id: str
    endpoint: str
    retrieved_at_utc: datetime
    row_count: int
    query: str | None


class SocrataAdapter:
    """Adapt the City of Calgary Socrata API to project-owned records.

    This object adapter delegates HTTP and JSON handling to a composed
    sodapy.Socrata client. It exposes iteration and download operations with
    project-specific validation, pagination safeguards, and metadata.

    Attributes:
        endpoint: Socrata resource endpoint.
        app_token: Optional application token supplied with requests.
    """

    def __init__(self, endpoint: str, app_token: str | None = None) -> None:
        """Configure the external source without making a network request.

        Args:
            endpoint: HTTP(S) URL ending in /resource/<dataset-id>.json, with
                no embedded query, fragment, or credentials.
            app_token: Optional Socrata application token sent as a header.

        Raises:
            ValueError: The endpoint is not a Socrata JSON resource URL.
        """
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or re.fullmatch(r"/resource/[a-z0-9]{4}-[a-z0-9]{4}\.json", parsed.path) is None
        ):
            raise ValueError("Expected a Socrata JSON resource URL without query or credentials.")
        self.endpoint = endpoint
        self.app_token = app_token

    def iter_records(
        self,
        *,
        select: str | None = None,
        where: str | None = None,
        page_size: int = 50_000,
    ) -> Iterator[dict[str, Any]]:
        """Yield all API rows using deterministic pagination.

        Args:
            select: Optional row-level SoQL select expression. Aggregate queries
                are not supported by the fixed row-identifier ordering.
            where: Optional SoQL filter expression.
            page_size: Maximum number of Socrata rows requested per page.

        Yields:
            One project-owned record for each row returned by the Socrata query.

        Raises:
            ValueError: page_size is not a positive integer, a query expression
                is blank or not a string, or a response is not a JSON list of objects.
            RuntimeError: A nonempty page repeats, suggesting pagination stalled.
            requests.RequestException: A permanent HTTP error occurs or transient
                failures exhaust three attempts for a page.

        Note:
            Pages are ordered by Socrata's unique :id field. Offset pagination
            does not freeze a changing dataset. Repeated-page detection compares
            row contents; selected fields should distinguish records to avoid
            treating identical projections as a repeated page. Each request has
            a 30-second timeout. Connection errors, timeouts, and HTTP 429, 500,
            502, 503, and 504 are retried after one and two seconds.
        """
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
            raise ValueError("page_size must be a positive integer.")
        params: dict[str, Any] = {"limit": page_size, "offset": 0, "order": ":id"}
        for name, expression in (("select", select), ("where", where)):
            if expression is not None:
                if not isinstance(expression, str) or not expression.strip():
                    raise ValueError(f"{name} must be a nonblank string when provided.")
                params[name] = expression

        seen_pages: set[bytes] = set()
        parsed = urlsplit(self.endpoint)
        dataset_id = parsed.path.rsplit("/", 1)[-1].removesuffix(".json")
        with Socrata(parsed.netloc, self.app_token, timeout=30) as client:
            # Preserve the endpoint scheme; sodapy otherwise defaults to HTTPS.
            client.uri_prefix = f"{parsed.scheme}://"
            while True:
                page = self._request_page(client, dataset_id, params)
                if not page:
                    return
                fingerprint = sha256(
                    json.dumps(page, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).digest()
                if fingerprint in seen_pages:
                    raise RuntimeError("Socrata returned a repeated page; pagination stopped.")
                seen_pages.add(fingerprint)
                yield from page
                if len(page) < page_size:
                    return
                params["offset"] += len(page)

    def _request_page(
        self, client: Socrata, dataset_id: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Fetch and validate a page, retrying only transient transport failures.

        Args:
            client: sodapy client owned by the current record iterator.
            dataset_id: Resource identifier passed to the external client.
            params: sodapy query options including the current page offset.

        Returns:
            Validated JSON objects with source field names and values preserved.

        Raises:
            ValueError: The response is invalid JSON or not a list of objects.
            requests.RequestException: The request fails permanently or after
                three attempts.
        """
        for attempt in range(3):
            try:
                try:
                    page = client.get(
                        dataset_id, content_type="json", format="application/json", **params
                    )
                except ValueError as exc:
                    raise ValueError("Socrata response is not valid JSON.") from exc
                if not isinstance(page, list) or any(
                    not isinstance(row, dict) for row in page
                ):
                    raise ValueError("Socrata response must be a JSON list of objects.")
                return page
            except requests.HTTPError as exc:
                if (
                    exc.response is None
                    or exc.response.status_code not in {429, 500, 502, 503, 504}
                    or attempt == 2
                ):
                    raise
            except (requests.ConnectionError, requests.Timeout):
                if attempt == 2:
                    raise
            sleep(2 ** attempt)
        raise RuntimeError("Socrata request attempts exhausted.")  # pragma: no cover

    def download(self, **query: Any) -> tuple[list[dict[str, Any]], DownloadMetadata]:
        """Materialize records and return them with retrieval metadata.

        Args:
            query: select, where, and page_size options forwarded to iter_records().

        Returns:
            The materialized records and their reproducibility metadata.

        Raises:
            TypeError: An unsupported query option is supplied.
            ValueError: Query options or a response are invalid.
            RuntimeError: Pagination returns a repeated page.
            requests.RequestException: Retrieval fails; no partial download or
                success metadata is returned.
        """
        records = list(self.iter_records(**query))
        metadata = DownloadMetadata(
            dataset_id=urlsplit(self.endpoint).path.rsplit("/", 1)[-1].removesuffix(".json"),
            endpoint=self.endpoint,
            retrieved_at_utc=datetime.now(timezone.utc),
            row_count=len(records),
            query=json.dumps(query, sort_keys=True) if query else None,
        )
        return records, metadata
