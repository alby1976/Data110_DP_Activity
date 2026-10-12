"""Recover missing permit communities from auditable location evidence.

This stage enriches cleaned permits using exact parcel addresses and local City
community polygons while leaving raw evidence intact.

Design Pattern:
    Pipes and Filters.

Pattern Rationale:
    An independent enrichment filter keeps geographic recovery outside cleaning
    and analysis and permits reuse of cached reference evidence.

Typical Usage:
    Append add_community_features to the pipeline's feature builders. Supply a
    WGS84 GeoJSON boundary file and a writable parcel-lookup cache path.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

from matplotlib.path import Path as PolygonPath
import pandas as pd
import requests

PARCEL_ENDPOINT = "https://data.calgary.ca/resource/9zvu-p8uz.json"


def _address(value: object) -> str:
    """Normalize spacing and case for an exact address comparison.

    Args:
        value: Source address, possibly missing.

    Returns:
        Uppercase address or empty text when missing.
    """
    return re.sub(r"\s+", " ", value.strip()).upper() if isinstance(value, str) else ""


def _parcel_cache(addresses: set[str], path: Path) -> dict:
    """Cache exact City parcel queries, including negative lookup results.

    Args:
        addresses: Normalized single addresses needed for this run.
        path: JSON cache; deleting it explicitly refreshes City reference data.

    Returns:
        Address keys mapped to lists of parcel records.

    Raises:
        requests.RequestException: A query fails; incomplete evidence is not used.
        ValueError: Cached or downloaded evidence has an unexpected structure.
        OSError: Cache reading or persistence fails.
    """
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "endpoint": PARCEL_ENDPOINT, "addresses": {},
    }
    if cache.get("endpoint") != PARCEL_ENDPOINT or not isinstance(cache.get("addresses"), dict):
        raise ValueError("Invalid parcel-address cache.")
    records = cache["addresses"]
    missing = sorted(addresses - records.keys())
    for start in range(0, len(missing), 25):
        batch = missing[start:start + 25]
        literals = ",".join("'" + address.replace("'", "''") + "'" for address in batch)
        response = requests.get(PARCEL_ENDPOINT, params={
            "$where": f"upper(address) in ({literals})", "$limit": 50000,
            "$select": "address,latitude,longitude",
        }, timeout=60)
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or len(rows) >= 50000:
            raise ValueError("Parcel-address response is invalid or truncated.")
        for address in batch:
            records[address] = [row for row in rows if _address(row.get("address")) == address]
    if missing:
        cache["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        temporary.replace(path)
    return records


def _community(
    point: tuple[float, float], features: list[dict], *,
    code_field: str = "comm_code", name_field: str = "name",
) -> tuple[str, str] | None:
    """Resolve an interior point to one community, respecting polygon holes.

    Args:
        point: Longitude and latitude in WGS84.
        features: City Polygon or MultiPolygon GeoJSON features.
        code_field: Polygon identifier property, including ward_num for wards.
        name_field: Polygon label property, including label for wards.

    Returns:
        Unique community code/name pair, or None for boundaries and ambiguity.

    Raises:
        ValueError: Reference geometry is unsupported.
    """
    matches = set()
    for feature in features:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"]
        if geometry["type"] == "Polygon":
            polygons = [polygons]
        elif geometry["type"] != "MultiPolygon":
            raise ValueError("Community boundaries must contain polygons.")
        for rings in polygons:
            # Points near any ring edge remain unresolved rather than depending
            # on floating-point boundary inclusion or ring winding direction.
            paths = [PolygonPath(ring) for ring in rings]
            near_edge = any(path.contains_point(point, radius=1e-9) !=
                            path.contains_point(point, radius=-1e-9) for path in paths)
            if near_edge:
                return None
            if paths[0].contains_point(point) and not any(
                path.contains_point(point) for path in paths[1:]
            ):
                properties = feature["properties"]
                code, name = properties.get(code_field), properties.get(name_field)
                if not code or not name:
                    raise ValueError(f"Polygons require {code_field} and {name_field}.")
                matches.add((code, name))
    return next(iter(matches)) if len(matches) == 1 else None


def add_community_features(
    permits: pd.DataFrame, *, boundary_path: Path, address_cache_path: Path,
) -> pd.DataFrame:
    """Fill missing community fields only when location evidence is unambiguous.

    Args:
        permits: Cleaned permits with optional communitycode, community, address,
            latitude, longitude, and locationcount fields.
        boundary_path: WGS84 City community Polygon/MultiPolygon GeoJSON file.
        address_cache_path: Persistent JSON cache for exact City parcel queries.

    Returns:
        Copy with missing communitycode/community values filled where supported,
        plus CommunityFillMethod, CommunityLookupStatus, and CommunityWasFilled.
        Raw columns, existing communities, coordinates, row order, and index are
        preserved. Missing communities remain available to analysis denominators.

    Raises:
        ValueError: Audit columns collide or boundaries use an unsupported CRS.
        OSError: Required reference files cannot be read or persisted.
        requests.RequestException: An uncached City address query fails.

    Note:
        Existing partial community values must agree with the spatial match.
        Multiple parcel matches are accepted only when every point resolves to
        the same community. Multi-location permits are left for review. Current
        boundaries recover a reference community, not historical membership.
        No network access occurs when all required addresses are cached.
    """
    result = permits.copy(deep=True)
    audits = {"CommunityFillMethod", "CommunityLookupStatus", "CommunityWasFilled"}
    if audits & set(result.columns):
        raise ValueError("Community audit columns already exist.")
    result["CommunityFillMethod"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result["CommunityLookupStatus"] = "source_complete"
    result["CommunityWasFilled"] = False
    # Minimal tables used by callers without geographic fields require no lookup.
    if not {"communitycode", "community"}.intersection(result.columns):
        result["CommunityLookupStatus"] = "fields_unavailable"
        return result
    for column in ("communitycode", "community"):
        if column not in result:
            result[column] = pd.NA
        result[column] = result[column].astype("string")
    missing = result[["communitycode", "community"]].isna().any(axis=1)
    if not missing.any():
        return result
    boundaries = json.loads(boundary_path.read_text(encoding="utf-8"))
    crs = boundaries.get("crs", {}).get("properties", {}).get("name", "")
    if crs and crs not in {"urn:ogc:def:crs:OGC:1.3:CRS84", "EPSG:4326"}:
        raise ValueError("Community lookup requires WGS84 longitude/latitude boundaries.")
    candidates = []
    needed = set()
    for position in range(len(result)):
        if not missing.iloc[position]:
            continue
        row = result.iloc[position]
        count = pd.to_numeric(row.get("locationcount"), errors="coerce")
        address = _address(row.get("address"))
        if (pd.notna(count) and count > 1) or ";" in address:
            result.iloc[position, result.columns.get_loc("CommunityLookupStatus")] = "multiple_locations"
            continue
        lat = pd.to_numeric(row.get("latitude"), errors="coerce")
        lon = pd.to_numeric(row.get("longitude"), errors="coerce")
        point = (float(lon), float(lat)) if pd.notna(lat) and pd.notna(lon) and \
            -90 <= lat <= 90 and -180 <= lon <= 180 else None
        if point is None and address:
            needed.add(address)
        candidates.append((position, point, address))
    parcels = _parcel_cache(needed, address_cache_path) if needed else {}
    for position, point, address in candidates:
        status, method, match = "no_location", None, None
        if point is not None:
            match = _community(point, boundaries["features"])
            status, method = "outside_or_ambiguous", "permit_coordinates"
        elif address:
            rows = parcels[address]
            resolved = []
            for row in rows:
                try:
                    parcel_point = (float(row["longitude"]), float(row["latitude"]))
                    resolved.append(_community(parcel_point, boundaries["features"]))
                except (KeyError, TypeError, ValueError):
                    resolved.append(None)
            if resolved and None not in resolved and len(set(resolved)) == 1:
                match = resolved[0]
            status, method = "address_unmatched_or_ambiguous", "parcel_address"
        if match:
            row = result.iloc[position]
            if any(pd.notna(row[column]) and str(row[column]).strip().upper() != value.upper()
                   for column, value in zip(("communitycode", "community"), match)):
                status = "source_conflict"
            else:
                for column, value in zip(("communitycode", "community"), match):
                    if pd.isna(row[column]):
                        result.iloc[position, result.columns.get_loc(column)] = value
                result.iloc[position, result.columns.get_loc("CommunityWasFilled")] = True
                result.iloc[position, result.columns.get_loc("CommunityFillMethod")] = method
                status = "filled"
        result.iloc[position, result.columns.get_loc("CommunityLookupStatus")] = status
    return result
