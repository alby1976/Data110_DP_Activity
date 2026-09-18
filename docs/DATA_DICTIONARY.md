# Data Dictionary

## Source fields

The source is the City of Calgary Development Permits dataset (`6933-unw5`). Field names below are the API names confirmed from the dataset metadata. The project will select only the fields needed for analysis while preserving `PermitNum` for traceability.

| Display name | API field | Type | Planned use |
|---|---|---|---|
| PermitNum | `permitnum` | text | unique permit identifier |
| Address | `address` | text | validation and drill-through; avoid unnecessary display |
| Category | `category` | text | permit/residential classification |
| Description | `description` | text | rule validation and development-type classification |
| ProposedUseCode | `proposedusecode` | text | proposed-use classification |
| ProposedUseDescription | `proposedusedescription` | text | readable proposed-use classification |
| PermittedDiscretionary | `permitteddiscretionary` | text | permitted/discretionary comparison |
| LandUseDistrict | `landusedistrict` | text | district analysis and rezoning-relevant flag |
| LandUseDistrictDescription | `landusedistrictdescription` | text | readable district context |
| Concurrent LOC | `concurrent_loc` | text | concurrent redesignation indicator |
| StatusCurrent | `statuscurrent` | text | current application status |
| AppliedDate | `applieddate` | date | primary study date and period assignment |
| DecisionDate | `decisiondate` | date | processing-time calculation |
| ReleaseDate | `releasedate` | date | secondary timing analysis |
| CanceledRefusedDate | `canceledrefuseddate` | date | cancellation/refusal timing |
| Decision | `decision` | text | decision outcome |
| DecisionBy | `decisionby` | text | decision authority |
| SDABNumber | `sdabnumber` | text | appeal indicator/reference |
| SDABHearingDate | `sdabhearingdate` | date | appeal timing |
| SDABDecision | `sdabdecision` | text | appeal outcome |
| SDABDecisionDate | `sdabdecisiondate` | date | appeal-decision timing |
| CommunityCode | `communitycode` | text | community key |
| CommunityName | `communityname` | text | community analysis and slicer |
| Ward | `ward` | text | ward analysis and slicer |
| Quadrant | `quadrant` | text | quadrant comparison |
| Latitude | `latitude` | text in source | map coordinate; convert to decimal number |
| Longitude | `longitude` | text in source | map coordinate; convert to decimal number |
| LocationCount | `locationcount` | text in source | multi-location quality check |
| LocationsGeoJSON | `locationsgeojson` | text | optional multi-location geography |

### Source cautions

- Several source fields can contain semicolon-separated values.
- Latitude and longitude are published as text and require numeric conversion.
- Current status is mutable and describes the record at retrieval time.
- A permit can have multiple locations; the point coordinate may not capture every location.
- The City states that records from 1979–2000 are more likely to be incomplete, although those years are outside the primary study window.

## Derived fields

| Field | Type | Description |
|---|---|---|
| `Period` | category | Before, During, Early Post-Repeal, or Outside Study Window |
| `AppliedYear` | integer | year from application date |
| `AppliedMonthNumber` | integer | 1–12 month number |
| `AppliedYearMonth` | date | first day of application month |
| `Season` | category | Fall (Sep–Nov), Winter (Dec–Feb), Spring (Mar–May), or Summer (Jun–Aug) |
| `SeasonStartDate` | date | first day of the season; Jan–Feb map to December 1 of the previous year |
| `SeasonLabel` | text | readable cross-year label, for example `Winter 2024–25` |
| `SeasonSortKey` | integer/date | chronological sort value derived from `SeasonStartDate` |
| `IsCompleteSeason` | Boolean | indicates whether the entire season is inside the applicable analysis window |
| `ProcessingDays` | integer | non-negative days from application to decision |
| `HasValidProcessingDays` | Boolean | validity flag for processing analysis |
| `IsResidential` | Boolean | reviewed residential classification |
| `ResidentialType` | category | standardized development/housing type |
| `RezoningRelevant` | Boolean | documented analytical relevance flag |
| `ClassificationRule` | text | rule or lookup entry producing the classification |
| `ClassificationNeedsReview` | Boolean | ambiguous or unmatched classification |
| `HasGeography` | Boolean | usable community or coordinate data |
| `IsPending` | Boolean | application has no final observed outcome at the snapshot date |
| `FollowUpDays` | integer | days from application to decision or, if unresolved, to the snapshot date |
| `HasMinimumFollowUp` | Boolean | record meets the documented follow-up requirement for its analysis |
| `IsRightCensored` | Boolean | final processing duration is not yet observed |
| `ExclusionReason` | text | explicit reason a record is omitted from a specific analytical subset |
| `DataRetrievedUTC` | datetime | source retrieval timestamp |
| `SourceSnapshotID` | text | identifier connecting outputs to the frozen source extract |

## Planned output tables

| File/table | Grain | Purpose |
|---|---|---|
| `permits_clean.csv` | one permit | Power BI fact table |
| `monthly_summary.csv` | period × month | trend validation and Python results |
| `seasonal_summary.csv` | period × season | seasonal volume and processing comparison |
| `type_summary.csv` | period × residential type | development-mix analysis |
| `community_summary.csv` | community | before/during geographic comparison |
| `processing_summary.csv` | period and optional type | processing-time statistics |
| `bias_audit.csv` | period × audit category | missingness, exclusions, pending cases, classification review, and valid denominators |
| `sensitivity_summary.csv` | scenario × metric | comparison of headline results under alternative reasonable rules |

Names are provisional until the Python workflow is implemented. The configured storage
formats may produce CSV files, Parquet files, or both. `storage.output_base_name` in
`config/settings.yaml` controls the shared stem used for generated data products when a
repository/exporter derives filenames from the storage settings.

## Configuration files

| File | Grain | Purpose |
|---|---|---|
| `config/settings.yaml` | one project configuration | data source, paths, study periods, analysis settings, seasons, quality checks, storage formats, output names, overwrite behavior, and logging archive settings |
| `config/classification_rules.csv` | one ordered classification rule | residential inclusion, housing-type, and rezoning-relevance logic, including validation status |

The classification-rule schema, precedence, validation, and audit requirements are defined in [Configuration and Classification Rules](CONFIGURATION.md). The rule file is an input and must not be overwritten as pipeline output.
