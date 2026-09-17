"""Adapter for the City of Calgary Socrata API."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DownloadMetadata:
    """Facts needed to reproduce a source download."""

    dataset_id: str
    endpoint: str
    retrieved_at_utc: datetime
    row_count: int
    query: str | None


class SocrataAdapter:
    """Retrieve paginated records without embedding analysis rules."""

    def __init__(self, endpoint: str, app_token: str | None = None) -> None:
        self.endpoint = endpoint
        self.app_token = app_token

    def iter_records(
        self,
        *,
        select: str | None = None,
        where: str | None = None,
        page_size: int = 50_000,
    ) -> Iterator[dict[str, Any]]:
        """Yield all API rows using deterministic pagination."""
        # TODO: Validate page_size and build SoQL parameters.
        # TODO: Request pages using $limit, $offset, and a stable $order.
        # TODO: Retry transient failures with a bounded backoff.
        # TODO: Validate that each response is a JSON list.
        # TODO: Stop on an empty/short page and guard against repeated pages.
        raise NotImplementedError

    def download(self, **query: Any) -> tuple[list[dict[str, Any]], DownloadMetadata]:
        """Materialize records and return them with retrieval metadata."""
        # TODO: Collect iter_records(), timestamp the completed retrieval, and count rows.
        raise NotImplementedError

