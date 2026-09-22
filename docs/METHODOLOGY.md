# Methodology

This document defines the analysis before results are calculated. Keeping these rules explicit reduces the risk of quietly changing the method after seeing the outcome.

## 1. Scope

### Primary question

What differences in Calgary residential development-permit activity can be observed before and during citywide rezoning?

### Unit of analysis

The source row represents a development-permit application. `PermitNum` is the expected unique identifier. Uniqueness will be tested after download; duplicate identifiers will be investigated rather than automatically discarded.

### Date used to assign the policy period

The primary classification uses `AppliedDate`, because the analysis concerns when an application was initiated. `DecisionDate` and `ReleaseDate` answer different questions and will remain available for processing-time and outcome analysis.

## 2. Study periods

| Label | Rule |
|---|---|
| Before | `2022-08-06 <= AppliedDate <= 2024-08-05` |
| During | `2024-08-06 <= AppliedDate <= 2026-08-03` |
| Early Post-Repeal | `AppliedDate >= 2026-08-04` |
| Outside Study Window | all earlier records |

The primary comparison is Before versus During. Early Post-Repeal is incomplete and contextual only.

### Sensitivity check

`add_period_features` is implemented as a pure table transformation. It uses
configured `StudyPeriod` values in order, includes the entire final calendar day,
and leaves missing/invalid dates unassigned. Valid dates in gaps or beyond closed
windows receive `Outside Study Window`. ISO offsets preserve source calendar
dates rather than shifting days. Cleaner invalid flags remain authoritative.

The filter adds ordered categorical `Period` and `DecisionPeriod`, nullable
`PeriodSortKey` (outside=0, configured periods=1 onward), and Boolean
`PeriodDateMissing`/`PeriodDateInvalid`. Nullable `CrossesPeriodBoundary` records
whether a nonnegative application-to-decision interval crosses a configured
start or exclusive end. Missing/invalid decisions or decisions preceding the
application leave this flag unknown. The CLI supplies the configured decision
field. No record is dropped or reassigned according to its decision date.

A secondary table should identify applications submitted before August 6, 2024 but decided afterward, and applications submitted before August 4, 2026 but decided afterward. These are not reclassified; they are reported so readers can see how applications cross policy boundaries.

## 3. Data acquisition

The analysis should retrieve data from the City of Calgary Socrata API and record:

- retrieval timestamp in UTC;
- dataset identifier;
- requested query or endpoint;
- number of rows returned;
- minimum and maximum `AppliedDate`;
- a local raw-file checksum, if a snapshot is saved.

The raw snapshot should remain unchanged. Cleaning and derived fields belong in processed outputs.

### Data provenance and reproducibility

The current exploratory review uses a frozen download of the City of Calgary's
**Development Permits** dataset (`6933-unw5`), retrieved through the project's
`SocrataAdapter` from `https://data.calgary.ca/resource/6933-unw5.json`.
The following facts come from the saved snapshot metadata rather than a later
query of the live source:

| Provenance field | Recorded value |
|---|---|
| Retrieval time (UTC) | September 22, 2026, 00:18:29.189616 |
| Study period | Before: August 6, 2022–August 5, 2024, inclusive |
| Selection field | Source `applieddate`, mapped to project `applied_date` |
| Downloaded records | 16,637; full selected-period download, not the earlier 500-record exploratory sample |
| API page size | 50,000 records per request; not a total-record limit |
| Raw storage | CSV and Parquet snapshots under `data/raw`, each with a `.metadata.json` sidecar |

The saved query filter is:

```sql
(applieddate >= '2022-08-06T00:00:00' AND applieddate < '2024-08-06T00:00:00')
```

Both snapshots use the filename stem
`development_permits_raw_Before_2022-08-06_2024-08-05_20260922_001829`.
Their separate SHA-256 checksums identify the exact serialized files:

| Format | SHA-256 |
|---|---|
| CSV | `1405729425ad356df41cff1cac46bef3f30a0709ce5d3cbd179baba953861005` |
| Parquet | `649e5e5d95b80003543b03facc372a5beeaea15746687c542f89b52798eded32` |

The [exploratory notebook](../notebooks/01_permit_exploration.ipynb) is pinned to
the Parquet snapshot and runs without another download. It verifies the checksum,
row count, dataset identity, saved query, and application dates against
`config/settings.yaml`. It also records hashes of the settings and
`config/classification_rules.csv` used for that execution. See the
[notebook explanation](../notebooks/01_permit_exploration_explaination.md) for the
meaning of the provenance and audit fields.

Data lineage is explicit: frozen source records are loaded, profiled, cleaned,
and classified using the versioned rule CSV. Cleaning retains source evidence in
`raw_` columns and preserves the input records and row index; classification
retains winning and additional matching rule IDs and review flags. Raw snapshots
remain in the ignored data directory, while code, configuration, and rules are
versioned. Credentials are excluded from the provenance record.

These checks establish consistency with the saved download, not independent
completeness or accuracy of the City's records. Source fields reflect the data
available at retrieval time, not necessarily their historical values when an
application was submitted. This snapshot covers only the Before period and does
not yet supply the full before/during comparison or evidence of completed housing
units. Subsequent downloads should retain their own metadata and checksums rather
than replace this provenance record.

## 4. Data-quality checks

`SchemaValidator` implements the structural check as an injected validation
strategy. The CLI supplies `quality_checks.required_columns` from
`config/settings.yaml`. It returns immutable `SchemaIssue` result objects:
missing required columns, duplicate column names, invalid column labels, and
unsupported table objects are errors; additional source or derived columns are
informational. Names are matched exactly without changing the table. Empty
tables may have valid schemas; identifier values, date validity, and row-count
checks belong to data-quality validation. The pipeline collects these findings;
returning an error finding does not itself stop execution.

`DataQualityValidator` implements record-level checks as a separate strategy and
returns immutable `QualityCheckResult` objects containing `check_name`,
`status` (`pass`, `warn`, or `fail`), `affected_rows`, and `message`. It never
repairs, drops, or reorders records. Missing identifiers fail; duplicate counts
include every member of a duplicate group, excluding null/blank identifiers.
`require_unique_permit_number: false` downgrades duplicates to warnings.
Missing application/decision dates and invalid dates are reported separately;
cleaner invalid flags preserve evidence when malformed values have become nulls.
A missing decision date does not alone establish that a permit is pending.

The three `warn_on_*` quality options default to true; false disables the
corresponding community, coordinate, or negative-duration check. Coordinate
checks distinguish missing values from malformed, nonfinite, or out-of-range
values, using latitude bounds of -90 to 90 and longitude bounds of -180 to 180.
Each coordinate check counts a row once even when both coordinates are affected.
Unavailable prerequisite columns produce failed results rather than silent
passes. Schema prerequisites and empty-table failures can have zero affected
rows, so consumers must inspect the status and message as well as the count.

Optional `quality_checks.minimum_row_count` fails when too few records are
loaded. Optional `max_data_age_days` requires an explicit ISO `reference_date`
and warns when the latest valid application date is older than that limit;
equality passes. These thresholds are nonnegative integers and are disabled
when omitted. Historical snapshots require a reference date appropriate to
their selected window, not an implicit comparison with today's date. Freshness
cannot be assessed without a valid application date and returns a failure in
that case. As with schema validation, result severity does not itself halt the
current pipeline.

The Python workflow should fail clearly or issue a documented warning for:

1. missing required columns;
2. duplicate or missing `PermitNum` values;
3. invalid dates;
4. `DecisionDate` earlier than `AppliedDate`;
5. missing community or coordinates;
6. unrecognized values in important categorical fields;
7. an unexpectedly small row count;
8. a maximum application date that suggests stale source data.

Missing values should not be silently converted into meaningful categories. Use an explicit label such as `Unknown` only in presentation fields while retaining a missing-value flag.

## 5. Residential classification

The exact residential filter must be based on observed values in `Category`, `Description`, `ProposedUseCode`, and `ProposedUseDescription`.

Recommended sequence:

1. list all distinct categories and proposed uses with counts;
2. create the version-controlled `config/classification_rules.csv` rule table described in [Configuration and Classification Rules](CONFIGURATION.md);
3. label each value as `Residential`, `NonResidential`, or `Review`;
4. inspect a sample of permit descriptions from each rule;
5. document rule coverage and the number of unmatched records;
6. keep the original fields beside the derived classification.

Do not rely on a loose keyword such as `house` without reviewing false positives and false negatives.

### Classification validation report

`ClassificationValidator` is an injected Strategy that returns a pandas Result
Table without changing permits or rules. Its `summary` row reports total,
matched, unmatched, and review counts; coverage and review percentages; separate
review/provisional/fallback status counts; overlapping-record and additional-match
counts; and unknown-rule, disabled-rule, and inconsistent-audit counts. The count
denominator is all input records. Empty inputs have undefined percentages rather
than an assumed 100% coverage.

The validator checks winning and additional recorded rule IDs, priority/ID order,
match counts, review flags, and stored outcomes against the supplied rule set.
It does not rerun matching predicates against source evidence. Missing audit
columns produce a failed assessment with unavailable metrics left null. Unknown
or disabled IDs and inconsistent audit evidence also fail. Unmatched or review
records produce warnings. Multiple matches alone do not fail validation because
broad fallback rules can intentionally overlap specific rules. The pipeline
collects these findings; a failed result does not itself halt execution.

For manual validation, supply an independent human-reviewed type column using
`audit_label_column`. Null and blank labels are excluded. Additional `confusion`
rows record observed expected/predicted class pairs and their `record_count`;
summary metrics remain null on those rows to avoid repeating totals. Filter by
`report_type` before aggregating the table. `audit_count`, `audit_error_count`,
and `audit_accuracy_percentage` describe only the labelled subset, comparing
labels exactly. A rule's validation-status text and its coverage are not evidence
of predictive accuracy, and sample accuracy is not automatically population
accuracy.

## 6. Rezoning-relevant classification

`RezoningRelevant` will be a transparent analytical flag, not an official City designation. Candidate evidence includes:

- land-use district values involving `R-CG`, `R-G`, or `H-GO`;
- proposed uses or reviewed descriptions involving rowhouses, townhouses, and other qualifying grade-oriented multi-unit housing forms;
- other rules added only after their source values are inspected.

The final logic should be stored in `config/classification_rules.csv` and summarized in the report. Rules will be evaluated by ascending priority, the first match will be recorded in `ClassificationRule`, and unmatched records will default to `Review` as specified by `config/settings.yaml`. All unmatched, conflicting, or ambiguous records should remain auditable.

## 7. Derived fields

| Field | Definition |
|---|---|
| `Period` | policy-period classification based on `AppliedDate` |
| `Year` | calendar year from `AppliedDate` |
| `MonthNumber` | month number from `AppliedDate` |
| `YearMonth` | first day of application month |
| `Season` | Fall, Winter, Spring, or Summer from `AppliedDate` |
| `SeasonStartDate` | first day of the three-month season; Winter starts December 1 |
| `SeasonLabel` | readable label such as `Winter 2024–25` |
| `SeasonSortKey` | chronological key based on `SeasonStartDate` |
| `IsCompleteSeason` | whether all days in that season fall inside the relevant analysis window |
| `ProcessingDays` | `DecisionDate - AppliedDate` in days |
| `HasValidProcessingDays` | both dates present and difference is non-negative |
| `ResidentialType` | reviewed rule-based housing/development category |
| `RezoningRelevant` | documented rule-based Boolean flag |
| `HasGeography` | valid community and/or coordinates available |

### Seasonal classification rules

`add_season_features` implements these rules as a pure, input-preserving filter.
The configured labels and ordered three-month lists partition all twelve months.
It adds `Season`, `SeasonStartDate`, inclusive `SeasonEndDate`, `SeasonLabel`,
integer `SeasonSortKey` (`YYYYMM`), and nullable `IsCompleteSeason` and
`IsPartialSeason`. Missing or invalid dates retain null features, including when
the cleaner has preserved an invalid-date flag. Calendar days are not shifted
by timezone offsets.

Completeness is evaluated against the individual configured policy window
containing the record, not the union of adjacent periods. An optional explicit
`observation_end` caps observed exposure. Without an upper bound, completeness
is unknown unless the season already starts before its policy window, proving
it partial. Dates outside supplied windows, beyond the observation end, or with
no supplied windows have unknown completeness. The CLI does not yet supply a
snapshot observation end, so open-ended periods retain this uncertainty.

| Season | Applied month | Season start |
|---|---|---|
| Fall | September, October, November | September 1 of the application year |
| Winter | December, January, February | December 1; January and February use the previous year |
| Spring | March, April, May | March 1 of the application year |
| Summer | June, July, August | June 1 of the application year |

Winter must not be split at January 1. For example, permits from December 2024, January 2025, and February 2025 all belong to `Winter 2024–25` with a `SeasonStartDate` of December 1, 2024.

The policy periods begin and end during August, so some Summer seasons are partial or split by the policy boundary. Seasonal totals must display `IsCompleteSeason`, and headline seasonal comparisons should use complete seasons or clearly normalize and label partial exposure.

## 8. Measures

### Permit volume

- total permits by period;
- permits per month;
- mean and median monthly permits;
- same-calendar-month comparison to reveal seasonality.
- permit counts and monthly average within each meteorological season;
- complete-season comparisons between the Before and During periods.

### Change

```text
AbsoluteChange = DuringCount - BeforeCount
PercentChange = (DuringCount - BeforeCount) / BeforeCount
```

Percentage change will be blank where the baseline is zero. Community tables will show the baseline count and use a minimum-baseline warning or filter.

### Development mix

```text
TypeShare = PermitsOfType / AllResidentialPermits
```

Counts and shares will both be shown.

### Processing time

Report count, median, mean, 25th percentile, and 75th percentile. The primary statistic is the median. Records without a valid application-to-decision interval are excluded from this measure but counted in a completeness table.

## 9. Analysis sequence

1. Retrieve and snapshot source data.
2. Profile schema, counts, missingness, dates, and categorical values.
3. Apply reviewed residential classification rules.
4. Create period and derived fields.
5. Validate classifications and date calculations.
6. Produce monthly, seasonal, type, community, and processing-time tables.
7. Export tidy tables in the configured CSV, JSON, JGeoJSON, and/or Parquet formats.
8. Reconcile headline totals between Python and Power BI.
9. Freeze the analysis snapshot used for the final presentation.

Project-wide dates, seasons, paths, warning thresholds, storage formats, overwrite behavior, log-archive settings, and output names must be read from `config/settings.yaml`. Classification outcomes must come from `config/classification_rules.csv`, not from duplicate hard-coded lists in notebooks, Python modules, or Power BI. Both files and the source snapshot identifier must be associated with the final results.

## 10. Verification and testing

On September 22, 2026, the exploratory notebook ran all nine code cells from a
fresh kernel against the frozen Before snapshot, including schema, data-quality,
and classification validation. No schema errors or classification audit
inconsistencies were found. Missing decision dates and geography, plus unmatched
and review classifications, remain warnings requiring investigation. Input
preservation and classification count reconciliation assertions passed. This
notebook execution is not the final pipeline smoke test and does not measure
human-label accuracy. Recorded counts and interpretation are in the
[notebook explanation](../notebooks/01_permit_exploration_explaination.md#recorded-before-snapshot-validation-results).

The project uses the behavior-first `pytest` framework defined in [Testing Framework](TESTING.md). Each non-package Python module has a matching test module. During scaffolding, a test reports `XFAIL` only when the target still raises `NotImplementedError`; this records unfinished work and does not count as a passed analytical check.

Verification will occur at five levels:

1. unit tests for individual functions and classes using small synthetic DataFrames;
2. integration tests across configuration, cleaning, classification, features, analyses, and exports;
3. data-contract tests for City source fields, rule-file schemas, output schemas, and allowed values;
4. an end-to-end smoke test using a named frozen source fixture and configuration version; and
5. reconciliation tests comparing Python results with Power BI measures.

Boundary cases must include both policy changes, December-to-February winter assignment, partial seasons, missing and invalid dates, pending cases, duplicate permit identifiers, unmatched and conflicting classification rules, missing geography, zero community baselines, and invalid processing durations. A module is not complete until its expected-failure marker is gone, its behavior and boundary cases pass, and the full suite remains green.

## 11. Interpretation rules

- Use **differed**, **increased**, **decreased**, or **was associated with**.
- Avoid **caused**, **resulted in**, or **impact** unless supported by a stronger causal design.
- Distinguish applications, decisions, releases, and approved permits.
- Label incomplete periods prominently.
- Report data-quality exclusions beside each affected metric.

## 12. Bias-control plan

The project will maintain a detailed [Biases and Mitigation Plan](BIAS_AND_MITIGATION.md). The minimum controls required before reporting results are:

1. freeze and identify the source-data snapshot used for the final analysis;
2. publish inclusion, exclusion, residential, and rezoning-relevant rules;
3. validate rule-based classifications against a seeded reproducible sample;
4. report missingness, exclusions, pending cases, and valid denominators;
5. distinguish applications, decisions, approvals, releases, and completed housing;
6. compare like months and complete seasons where possible;
7. flag partial seasons, right-censored processing times, and small community baselines;
8. report citywide and subgroup results to check for aggregation effects;
9. run sensitivity analyses using reasonable alternative dates and classification rules;
10. write conclusions from the results table rather than selecting only supportive charts.

Bias controls and unresolved residual risks will be included in the final report. A mitigation step must not be described as eliminating a bias unless evidence demonstrates that it does.

## 13. Reproducibility checklist

- [ ] Data retrieval timestamp recorded
- [ ] Dependencies pinned
- [ ] `config/settings.yaml` validated and associated with the final run
- [ ] Storage formats, output basename, overwrite behavior, and log archive settings recorded
- [ ] `config/classification_rules.csv` populated, validated, and committed
- [ ] Raw data excluded from Git if large or frequently refreshed
- [ ] Processed tables generated by code
- [ ] Python totals reconciled with Power BI measures
- [ ] Final figures traceable to a named data snapshot
- [ ] README commands tested on a clean environment
- [ ] All scaffold-related `XFAIL` results removed
- [ ] Unit, boundary, missing-value, and invalid-input tests pass
- [ ] Frozen-fixture integration and end-to-end smoke tests pass
- [ ] Python and Power BI reconciliation tests pass
- [ ] Bias register completed with evidence for each applied mitigation
- [ ] Sensitivity results retained, including results that weaken the main finding
