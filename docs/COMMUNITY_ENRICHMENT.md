# Automated community recovery

The normal CLI `run` command now fills missing `communitycode` and `community`
fields before validation, analysis, and export. Enable or disable this stage in
`analysis.community_enrichment` in `config/settings.yaml`.

Cleaning excludes null, empty, and whitespace-only addresses before lookup.
Literal `undefine` and `undefined` addresses are retained. Raw snapshots remain
unchanged; downstream counts use the retained records.

```powershell
python -m dp_activity.cli --settings config/settings.yaml run data/raw/development_permits_20260925_045241.csv
```

The stage uses valid permit coordinates when available. Otherwise it queries
the City of Calgary Parcel Address API (`9zvu-p8uz`) for an exact address match,
then checks which community polygon contains the parcel point. It supports
Polygon and MultiPolygon geometry, including holes. Reference polygons must
use WGS84 longitude/latitude coordinates.

The configured boundary reference is
`data/processed/Community_District_Boundaries_20261010.geojson`. Its community
properties are `comm_code` and `name`. The first run queries uncached addresses
and saves records, negative results, endpoint, and retrieval time in
`data/interim/parcel_address_cache.json`. Later runs reuse this cache without
network access. Archive or delete this cache when deliberately refreshing
parcel evidence; changing the boundary file also changes the recovery reference.

Only missing processed community values are filled. Existing partial values must
agree with the lookup. Raw columns, source snapshots, and permit coordinates
remain intact. Reference boundaries describe their published geography; inferred
communities are not certified historical assignments for the permit date.

Exported audit columns:

| Field | Meaning |
| --- | --- |
| `CommunityWasFilled` | At least one missing community field was recovered. |
| `CommunityFillMethod` | `permit_coordinates` or `parcel_address` for a recovery. |
| `CommunityLookupStatus` | `filled`, `source_complete`, `source_conflict`, `multiple_locations`, `no_location`, `outside_or_ambiguous`, `address_unmatched_or_ambiguous`, or `fields_unavailable`. |

Multiple parcel records are accepted only when all resolve to the same community.
Boundary points, conflicting existing values, multi-location permits, and
unmatched addresses remain unresolved. Missing communities continue to be
included in the analytical denominators. Failed API requests stop the run rather
than silently producing partially enriched exports.

The first lookup on the September 25 snapshot recovered 41 of 54 missing
communities. Nine addresses were unresolved and four permits had no location.
The initial review extract is `data/interim/community_lookup_review.csv`.
