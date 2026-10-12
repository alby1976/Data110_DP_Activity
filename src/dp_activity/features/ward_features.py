"""Recover missing permit wards from exact City parcel-address matches.

This stage reuses cached parcel evidence and polygon containment to fill missing
wards before geographic analysis, preserving existing ward and raw values.

Design Pattern:
    Pipes and Filters.

Pattern Rationale:
    A separate enrichment filter isolates geographic recovery from source
    cleaning and reporting while reusing community lookup infrastructure.

Typical Usage:
    Append add_ward_features to pipeline feature builders with writable local
    ward-boundary and parcel-address cache paths.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import requests

from dp_activity.features.community_features import _address, _community, _parcel_cache

WARD_ENDPOINT = "https://data.calgary.ca/resource/tz8z-hyaz.geojson"


def _boundaries(path: Path) -> dict:
    """Refresh the local WGS84 ward reference from the City on every invocation.

    Args:
        path: GeoJSON reference path atomically replaced after validation.

    Returns:
        Validated FeatureCollection with source endpoint and retrieval time.

    Raises:
        ValueError: Response is truncated, malformed, or uses a different CRS.
        requests.RequestException: The reference download fails.
        OSError: Reference reading or persistence fails.
    """
    response = requests.get(WARD_ENDPOINT, params={"$limit": 1000}, timeout=60)
    response.raise_for_status()
    data = response.json()
    data["source_endpoint"] = WARD_ENDPOINT
    data["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    features = data.get("features")
    if data.get("type") != "FeatureCollection" or not features or len(features) >= 1000:
        raise ValueError("Ward reference must be a complete GeoJSON FeatureCollection.")
    crs = data.get("crs", {}).get("properties", {}).get("name", "")
    if crs and crs not in {"urn:ogc:def:crs:OGC:1.3:CRS84", "EPSG:4326"}:
        raise ValueError("Ward reference requires WGS84 longitude/latitude.")
    for feature in features:
        properties = feature["properties"]
        if not str(properties.get("ward_num", "")).isdigit() or not properties.get("label"):
            raise ValueError("Ward reference requires ward_num and label properties.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    temporary.replace(path)
    return data


def add_ward_features(
    permits: pd.DataFrame, *, boundary_path: Path, address_cache_path: Path,
) -> pd.DataFrame:
    """Fill only blank or null wards using unambiguous exact-address evidence.

    Args:
        permits: Cleaned permits with ward, address, and optional locationcount.
        boundary_path: Official City WGS84 ward polygons refreshed on each run.
        address_cache_path: Parcel cache shared with community enrichment.

    Returns:
        Copy with recovered wards and WardWasFilled, WardFillMethod,
        WardLookupStatus, and WardBoundaryReference audit columns. Existing
        nonblank ward values and all raw columns remain unchanged. Ambiguous or
        unmatched addresses remain unresolved, retaining row order and index.

    Raises:
        ValueError: Audit columns collide or reference evidence is invalid.
        requests.RequestException: A reference refresh or uncached address query fails.
        OSError: Local reference reading or persistence fails.

    Note:
        Current boundaries yield current reference wards, not historical wards
        at application time. Multi-location permits require review. Multiple
        parcel records must all resolve to the same ward. Only exact address
        matches are used; no community-centroid or street-name inference occurs.
    """
    result = permits.copy(deep=True)
    audits = {"WardWasFilled", "WardFillMethod", "WardLookupStatus", "WardBoundaryReference"}
    if audits & set(result):
        raise ValueError("Ward audit columns already exist.")
    result["WardWasFilled"] = False
    result["WardFillMethod"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result["WardLookupStatus"] = "source_complete"
    result["WardBoundaryReference"] = pd.Series(pd.NA, index=result.index, dtype="string")
    if "ward" not in result:
        result["WardLookupStatus"] = "fields_unavailable"
        return result
    boundaries = _boundaries(boundary_path)
    missing = result["ward"].isna() | result["ward"].map(
        lambda value: isinstance(value, str) and not value.strip()
    )
    positions = [position for position in range(len(result)) if missing.iloc[position]]
    if not positions:
        return result
    needed, candidates = set(), []
    for position in positions:
        row = result.iloc[position]
        address = _address(row.get("address"))
        count = pd.to_numeric(row.get("locationcount"), errors="coerce")
        status = "address_unmatched_or_ambiguous" if address else "no_address"
        if ";" in address or (pd.notna(count) and count > 1):
            status = "multiple_locations"
        elif address:
            needed.add(address)
            candidates.append((position, address))
        result.iloc[position, result.columns.get_loc("WardLookupStatus")] = status
    if not candidates:
        return result
    parcels = _parcel_cache(needed, address_cache_path)
    # Object permits a recovered numeric ward alongside source text or numbers.
    result["ward"] = result["ward"].astype(object)
    for position, address in candidates:
        matches = []
        for parcel in parcels[address]:
            try:
                point = (float(parcel["longitude"]), float(parcel["latitude"]))
            except (KeyError, TypeError, ValueError):
                matches.append(None)
                continue
            matches.append(_community(point, boundaries["features"],
                                      code_field="ward_num", name_field="label"))
        result.iloc[position, result.columns.get_loc("WardBoundaryReference")] = boundary_path.name
        if matches and None not in matches and len(set(matches)) == 1:
            result.iloc[position, result.columns.get_loc("ward")] = int(matches[0][0])
            result.iloc[position, result.columns.get_loc("WardWasFilled")] = True
            result.iloc[position, result.columns.get_loc("WardFillMethod")] = "parcel_address"
            result.iloc[position, result.columns.get_loc("WardLookupStatus")] = "filled"
    return result
