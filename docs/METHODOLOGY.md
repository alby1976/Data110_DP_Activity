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

## 4. Data-quality checks

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
2. create a version-controlled lookup table;
3. label each value as `Include`, `Exclude`, or `Review`;
4. inspect a sample of permit descriptions from each rule;
5. document rule coverage and the number of unmatched records;
6. keep the original fields beside the derived classification.

Do not rely on a loose keyword such as `house` without reviewing false positives and false negatives.

## 6. Rezoning-relevant classification

`RezoningRelevant` will be a transparent analytical flag, not an official City designation. Candidate evidence includes:

- land-use district values involving `R-CG`, `R-G`, or `H-GO`;
- proposed uses or reviewed descriptions involving rowhouses, townhouses, and other qualifying grade-oriented multi-unit housing forms;
- other rules added only after their source values are inspected.

The final logic should be stored in a lookup/configuration file and summarized in the report. All unmatched or ambiguous records should remain auditable.

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
7. Export tidy CSV tables for Power BI.
8. Reconcile headline totals between Python and Power BI.
9. Freeze the analysis snapshot used for the final presentation.

## 10. Interpretation rules

- Use **differed**, **increased**, **decreased**, or **was associated with**.
- Avoid **caused**, **resulted in**, or **impact** unless supported by a stronger causal design.
- Distinguish applications, decisions, releases, and approved permits.
- Label incomplete periods prominently.
- Report data-quality exclusions beside each affected metric.

## 11. Reproducibility checklist

- [ ] Data retrieval timestamp recorded
- [ ] Dependencies pinned
- [ ] Classification lookup committed
- [ ] Raw data excluded from Git if large or frequently refreshed
- [ ] Processed tables generated by code
- [ ] Python totals reconciled with Power BI measures
- [ ] Final figures traceable to a named data snapshot
- [ ] README commands tested on a clean environment
