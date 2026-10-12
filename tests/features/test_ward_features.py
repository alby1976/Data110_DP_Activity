"""Verify exact-address ward recovery without altering source evidence.

Frozen references exercise missing wards and conservative handling of ambiguity.

Design Pattern:
    None.

Pattern Rationale:
    Direct tests verify the filter's public behavior using independent fixtures.

Typical Usage:
    Run with pytest as part of the feature test suite.
"""

import json

import pandas as pd
import pytest

from dp_activity.features.community_features import PARCEL_ENDPOINT
from dp_activity.features.ward_features import WARD_ENDPOINT, _boundaries, add_ward_features


def test_fill_blank_and_null_wards_preserving_existing_values(tmp_path):
    """Fill only missing wards, retaining ambiguity, row indices, and raw evidence.

    Args:
        tmp_path: Temporary directory for frozen lookup references.
    """
    boundary = tmp_path / "wards.geojson"
    boundary.write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "geometry": {"type": "Polygon", "coordinates": [
            [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
        ]}, "properties": {"ward_num": "4", "label": "WARD 4"},
    }]}))
    cache = tmp_path / "parcels.json"
    cache.write_text(json.dumps({"endpoint": PARCEL_ENDPOINT, "addresses": {
        "10 MAIN ST": [{"longitude": 2, "latitude": 2}],
        "20 MAIN ST": [{"longitude": 2, "latitude": 2}, {"longitude": 8, "latitude": 8}],
    }}))
    source = pd.DataFrame({
        "address": ["10 MAIN ST", "10 main st", "10 MAIN ST", "20 MAIN ST", "10 MAIN ST", None],
        "ward": [None, " \t ", "9", None, None, None],
        "raw_ward": [None, " \t ", "9", None, None, None],
        "locationcount": [1, 1, 1, 1, 2, 1],
    }, index=[1, 1, 2, 3, 4, 5])
    original = source.copy(deep=True)
    result = add_ward_features(source, boundary_path=boundary, address_cache_path=cache)
    assert result["ward"].iloc[:3].tolist() == [4, 4, "9"]
    assert result["WardLookupStatus"].tolist() == [
        "filled", "filled", "source_complete", "address_unmatched_or_ambiguous",
        "multiple_locations", "no_address",
    ]
    assert result["WardWasFilled"].sum() == 2
    pd.testing.assert_series_equal(result["raw_ward"], source["raw_ward"])
    pd.testing.assert_frame_equal(source, original)
    assert result.index.equals(source.index)


def test_ward_boundaries_download_once_and_validate_crs(tmp_path, requests_mock):
    """Persist an official reference once and reject projected coordinates.

    Args:
        tmp_path: Temporary reference directory.
        requests_mock: Mock City HTTP responses.
    """
    data = {"type": "FeatureCollection", "features": [{
        "properties": {"ward_num": "1", "label": "WARD 1"},
    }]}
    requests_mock.get(WARD_ENDPOINT, json=data)
    path = tmp_path / "wards.geojson"
    assert _boundaries(path)["source_endpoint"] == WARD_ENDPOINT
    assert _boundaries(path)["retrieved_at_utc"]
    assert requests_mock.call_count == 1
    data["crs"] = {"properties": {"name": "EPSG:3857"}}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="WGS84"):
        _boundaries(path)
