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
| `DecisionPeriod` | ordered category | configured period of decision; missing when unavailable or invalid |
| `PeriodSortKey` | nullable integer | outside=0; configured periods=1 onward; missing for unknown application dates |
| `PeriodDateMissing` | Boolean | genuinely absent primary date, excluding cleaner-flagged invalid values |
| `PeriodDateInvalid` | Boolean | malformed primary date or retained cleaner invalid flag |
| `CrossesPeriodBoundary` | nullable Boolean | nonnegative application-to-decision interval crosses a configured boundary; unknown when dates are unusable |
| `AppliedYear` | integer | year from application date |
| `AppliedMonthNumber` | integer | 1–12 month number |
| `AppliedYearMonth` | date | first day of application month |
| `Season` | category | Fall (Sep–Nov), Winter (Dec–Feb), Spring (Mar–May), or Summer (Jun–Aug) |
| `SeasonStartDate` | date | first day of the season; Jan–Feb map to December 1 of the previous year |
| `SeasonEndDate` | date | inclusive last calendar day of the three-month season |
| `IsPartialSeason` | nullable Boolean | inverse of known season completeness; null when exposure cannot be established |
| `SeasonLabel` | text | readable cross-year label, for example `Winter 2024–25` |
| `SeasonSortKey` | integer/date | chronological sort value derived from `SeasonStartDate` |
| `IsCompleteSeason` | Boolean | indicates whether the entire season is inside the applicable analysis window |
| `ProcessingDays` | nullable integer | signed calendar days from application to decision; retain negatives for audit and filter HasValidProcessingDays for summaries |
| `HasNegativeProcessingDays` | Boolean | decision calendar date precedes application date |
| `ProcessingDateMissing` | Boolean | either required date genuinely absent, excluding invalid evidence |
| `ProcessingDateInvalid` | Boolean | either date malformed or flagged invalid by the cleaner |
| `IsAfterObservationEnd` | Boolean | either date exceeds an explicitly supplied observation horizon; false without a horizon |
| `HasValidProcessingDays` | Boolean | validity flag for processing analysis |
| `IsResidential` | Boolean | reviewed residential classification |
| `ResidentialType` | category | standardized development/housing type |
| `RezoningRelevant` | Boolean | documented analytical relevance flag |
| `ClassificationRule` | text | rule or lookup entry producing the classification |
| `ClassificationNeedsReview` | Boolean | ambiguous or unmatched classification |
| `IncludeResidential` | Boolean | first matching rule's inclusion decision; false for unmatched records pending review |
| `ValidationStatus` | text | winning rule's evidence status, or `unmatched` |
| `ClassificationMatchCount` | integer | number of enabled rules matching the permit |
| `ClassificationConflictCount` | integer | additional matches after the winner; potential overlap even when outcomes agree |
| `ClassificationMatchedRules` | tuple of text | all matching rule IDs in priority/ID order |
| `HasGeography` | Boolean | usable community or coordinate data |
| `IsPending` | Boolean | analytical proxy: usable application with genuinely missing decision; not an official status; excludes applications beyond an explicit horizon |
| `FollowUpDays` | integer | days from application to decision or, if unresolved, to the snapshot date |
| `HasMinimumFollowUp` | Boolean, planned | record meets a future documented follow-up requirement; not yet generated |
| `IsRightCensored` | Boolean | final processing duration is not yet observed |
| `ExclusionReason` | text | explicit reason a record is omitted from a specific analytical subset |
| `DataRetrievedUTC` | datetime | source retrieval timestamp |
| `SourceSnapshotID` | text | identifier connecting outputs to the frozen source extract |

## Configured and planned output tables

### Implemented validation results

These reports are produced in Python; their final file export remains pending.

| Report | Grain | Fields and interpretation |
|---|---|---|
| Schema issues | one structural finding | `severity` (`error`/`info`), `column`, `message`; returned as frozen `SchemaIssue` objects |
| Quality checks | one executed check or missing prerequisite | `check_name`, `status` (`pass`/`warn`/`fail`), `affected_rows`, `message`; returned as frozen `QualityCheckResult` objects |
| Classification summary | one row with `report_type=summary` | `record_count`, `matched_count`, `unmatched_count`, `coverage_percentage`, `unmatched_percentage`, `review_count`, `review_percentage` |
| Classification evidence | fields on the summary row | `overlap_count`, `additional_match_count`, `unknown_rule_count`, `disabled_rule_count`, `inconsistent_audit_count`, `missing_audit_columns`, `enabled_rule_count`, and separate `review_status_count`, `provisional_status_count`, `fallback_status_count` |
| Human-label audit | fields on the summary row when requested | `audit_count`, `audit_error_count`, `audit_accuracy_percentage`; denominator is only independently labelled records |
| Confusion matrix | one observed expected/predicted pair, `report_type=confusion` | `expected_type`, `predicted_type`, `record_count`, `status`, `message`; summary metrics are null on these rows |

Classification rows also contain `status` and `message`. Filter `report_type`
before aggregating counts. Unavailable metrics and undefined percentages are
null, not zero. Overlaps are not automatically errors; coverage is not accuracy.
Quality checks can fail with zero affected rows when columns are missing or a
required nonempty dataset is empty. Inspect status and message as well as counts.

### Planned exported products

`TypeAnalysis` returns in-memory `type_summary` (period × included residential
type) with `PermitCount`, `PeriodResidentialCount`, fractional `TypeShare`,
`BaselinePeriod`, `BaselinePermitCount`, `AbsoluteChange`, `PercentChange`, and
`ShareChangePercentagePoints`. It also returns `type_period_totals` (one row per
period) with `AllPermitCount`, `PeriodResidentialCount`, and `ExcludedCount`.
Unknown types remain in the denominator; empty denominators produce null shares.
Export mapping for these tables remains pending.

`VolumeAnalysis` now returns in-memory `permit_volume` (one row per period) and
`monthly_volume` (one row per period/month), including zero months. Both contain
`PermitCount`, `AllPermitCount`, `ExcludedCount`, `ResidentialShare`,
`ExposureDays`, and `WindowSource`. Monthly rows add `YearMonth` and nullable
`IsPartialMonth`. Period rows add `MonthCount`, `MeanMonthlyCount`,
`MedianMonthlyCount`, `WindowStart`, `WindowEnd`, `BaselinePeriod`,
`AbsoluteChange`, and `PercentChange`. Shares are fractions; changes are percent
units. Final filename mapping and export remain pending.

| File/table | Grain | Purpose |
|---|---|---|
| `permits_clean` | one permit | Power BI fact table |
| `monthly_summary` | period × month | trend validation and Python results |
| `seasonal_summary` | period × season | seasonal volume and processing comparison |
| `type_summary` | period × residential type | development-mix analysis |
| `community_summary` | community | before/during geographic comparison |
| `processing_summary` | period and optional type | processing-time statistics |
| `bias_audit` | period × audit category | missingness, exclusions, pending cases, classification review, and valid denominators |

These extension-free labels are configured in `config/settings.yaml`. Additional analytical tables,
such as a future `sensitivity_summary`, should be added to `outputs` before they are
treated as pipeline products. The configured storage formats may produce CSV, JSON,
JGeoJSON, Parquet files, or a combination. `storage.output_base_name` controls the
shared stem used for generated data products when a repository/exporter derives
filenames from the storage settings.
The documented naming convention is
`base_label[_study_period_label][_period][_timestamp][_current_date_time].format`;
consuming output labels and the additional optional current-date/time component
remain exporter work. See [Configuration](CONFIGURATION.md) for implementation limits.

## Configuration files

| File | Grain | Purpose |
|---|---|---|
| `config/settings.yaml` | one project configuration | data source, paths, study periods, analysis settings, seasons, quality checks, storage formats, output names, overwrite behavior, and logging archive settings |
| `config/classification_rules.csv` | one ordered classification rule | residential inclusion, housing-type, and rezoning-relevance logic, including validation status |

The classification-rule schema, precedence, validation, and audit requirements are defined in [Configuration and Classification Rules](CONFIGURATION.md). The rule file is an input and must not be overwritten as pipeline output.
