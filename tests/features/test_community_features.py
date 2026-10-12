"""Verify conservative community enrichment and preservation of source evidence.

Tests exercise polygon holes, ambiguous matches, and cached address recovery.

Design Pattern:
    None.

Pattern Rationale:
    Direct fixture-based tests verify observable enrichment behavior.

Typical Usage:
    Run with pytest alongside the other feature tests.
"""

import json

import pandas as pd

from dp_activity.features.community_features import (
    PARCEL_ENDPOINT, _community, _parcel_cache, add_community_features,
)


def _feature(code="AAA", name="ALPHA", holes=False):
    """Build a small WGS84 polygon for controlled location tests.

    Args:
        code: Community identifier.
        name: Community label.
        holes: Include an interior exclusion ring.

    Returns:
        GeoJSON polygon feature.
    """
    rings = [[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]]
    if holes:
        rings.append([[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]])
    return {"geometry": {"type": "Polygon", "coordinates": rings},
            "properties": {"comm_code": code, "name": name}}


def test_polygon_holes_edges_and_overlaps():
    """Leave holes, shared edges, and overlapping communities unresolved."""
    assert _community((3, 3), [_feature(holes=True)]) == ("AAA", "ALPHA")
    assert _community((1.5, 1.5), [_feature(holes=True)]) is None
    assert _community((0, 2), [_feature()]) is None
    assert _community((3, 3), [_feature(), _feature("BBB", "BETA")]) is None


def test_cached_enrichment_preserves_source_and_rejects_conflicts(tmp_path):
    """Recover exact addresses while retaining conflicts and multiple locations.

    Args:
        tmp_path: Isolated reference-file directory supplied by pytest.
    """
    boundary = tmp_path / "boundaries.json"
    boundary.write_text(json.dumps({"features": [_feature()]}))
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps({"endpoint": PARCEL_ENDPOINT, "addresses": {
        "10 MAIN ST": [{"longitude": 3, "latitude": 3}],
        "20 MAIN ST": [{"longitude": 3, "latitude": 3}, {"longitude": 10, "latitude": 10}],
    }}))
    source = pd.DataFrame({
        "address": ["10 main st", "10 MAIN ST", "20 MAIN ST", "10 MAIN ST", "10 MAIN ST"],
        "communitycode": [None, "BBB", None, None, "AAA"],
        "community": [None, None, None, None, "ALPHA"],
        "raw_community": [None] * 5,
        "locationcount": [1, 1, 1, 2, 1],
    }, index=[7, 7, 9, 10, 11])
    original = source.copy(deep=True)
    result = add_community_features(source, boundary_path=boundary, address_cache_path=cache)
    assert result.iloc[0]["community"] == "ALPHA"
    assert result.iloc[0]["CommunityFillMethod"] == "parcel_address"
    assert result["CommunityLookupStatus"].tolist() == [
        "filled", "source_conflict", "address_unmatched_or_ambiguous",
        "multiple_locations", "source_complete",
    ]
    assert result["raw_community"].isna().all()
    pd.testing.assert_frame_equal(source, original)
    assert result.index.equals(source.index)


def test_parcel_queries_cache_negative_results_and_escape_literals(tmp_path, requests_mock):
    """Cache missing addresses and safely quote City query literals.

    Args:
        tmp_path: Isolated cache directory supplied by pytest.
        requests_mock: HTTP fixture that avoids external service dependencies.
    """
    requests_mock.get(PARCEL_ENDPOINT, json=[])
    path = tmp_path / "cache.json"
    assert _parcel_cache({"1 O'NEIL ST"}, path) == {"1 O'NEIL ST": []}
    assert "O''NEIL" in requests_mock.last_request.qs["$where"][0].upper()
    _parcel_cache({"1 O'NEIL ST"}, path)
    assert requests_mock.call_count == 1
