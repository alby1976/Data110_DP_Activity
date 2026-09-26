# Guide to `02_complete_period_exploration.ipynb`

This document accompanies [the complete-period exploratory notebook](02_complete_period_exploration.ipynb). It explains the workflow, displayed values, recorded findings, and interpretation limits. The notebook extends the [Before-only exploration](01_permit_exploration.ipynb) to all three configured study periods and adds community and ward comparisons.

The unit of observation is a **development-permit application record**. Counts do not measure dwelling units, approvals, construction starts, or completed homes.

## 1. Snapshot and study coverage

The verified run used the City of Calgary Development Permits dataset, `6933-unw5`, downloaded through the project's paginated Socrata adapter. The download retrieved all records matching the configured application-date filter, without a sample limit.

| Snapshot detail | Recorded value |
|---|---|
| Parquet file used for analysis | `data/raw/development_permits_20260925_045241.parquet` |
| Companion CSV | `data/raw/development_permits_20260925_045241.csv` |
| Metadata | Each snapshot has an adjacent `.metadata.json` sidecar |
| Retrieval time | September 25, 2026, 04:52:41 UTC; September 24 locally in Edmonton |
| Raw records / columns | 31,339 / 34 |
| Earliest application | August 6, 2022 |
| Latest observed application | September 23, 2026 |
| Analysis observation horizon | September 25, 2026, from the UTC retrieval date |

All period boundaries below are inclusive.

| Period | Window start | Analysis window end | Exposure days | All records | Included residential | Excluded from residential analysis |
|---|---|---|---:|---:|---:|---:|
| Before | 2022-08-06 | 2024-08-05 | 731 | 16,637 | 7,940 | 8,697 |
| During | 2024-08-06 | 2026-08-03 | 728 | 13,866 | 6,038 | 7,828 |
| Early Post-Repeal | 2026-08-04 | 2026-09-25 | 53 | 836 | 299 | 537 |
| Total | | | | 31,339 | 14,277 | 17,062 |

“Complete period” means the download includes all configured study windows and all matching records returned by the source. It does **not** mean the open-ended post-repeal period is finished or that every real-world application has already been reported. The latest observed application precedes the retrieval horizon by two calendar days. Exposure uses the retrieval-date convention, including the retrieval day, rather than inferring coverage from the latest record.

## 2. Running and refreshing the notebook

Run cells from top to bottom with the project's configured Python environment. The verified environment reported Python 3.13.14, pandas 2.2.3, and Matplotlib 3.10.8. Parquet support is required to load the pinned snapshot.

| Setting | Default / purpose |
|---|---|
| `SETTINGS_PATH` | Loads `config/settings.yaml` from the repository root |
| `SNAPSHOT_FILENAME` | Pins the Parquet snapshot listed above |
| `REFRESH_DOWNLOAD` | `False`: reuses the snapshot offline |
| `REVIEW_LIMIT` | `10`: limits displayed examples, not analyzed records |
| `INCLUDE_PARTIAL_SEASONS` | `False`: seasonal charts use complete seasons |
| `SEASON_YEAR_METRIC` | `"PermitCount"`: season/year heatmap shows counts; `"DP_Rate30"` selects rates |
| `EXPORT_EXPLORATORY_OUTPUTS` | `False`: set true in the optional export cell to save tables and PNG charts |

To deliberately obtain a new snapshot:

1. Set `REFRESH_DOWNLOAD=True` and run the setup/download cell.
2. Copy the printed Parquet filename into `SNAPSHOT_FILENAME`.
3. Set `REFRESH_DOWNLOAD=False` and rerun the notebook from the top.
4. Recheck coverage, validation, and findings; this document's recorded numbers describe the original pinned run.

Refreshing writes new timestamped CSV and Parquet snapshots and metadata. It updates the filename in kernel memory but does not automatically rewrite the filename in the cell source. With optional exports disabled, ordinary offline runs create no external analysis-table or chart exports; outputs are displayed in the notebook.

The raw snapshot is frozen, but settings and classification rules are read from the current project files. Their displayed hashes help identify changes; they do not freeze those files or guarantee the same classifications after edits.

## 3. Provenance and coverage checks

Before analysis, the notebook checks the snapshot's SHA-256 checksum, metadata row count, dataset identifier, and saved query against the configured download query. It also requires valid application dates within the study start and observation horizon and reconciles period counts to the loaded total.

| Coverage-table field | Meaning |
|---|---|
| `WindowStart`, `WindowEnd` | Inclusive analysis boundaries, capped at the observation horizon |
| `ExposureDays` | Calendar days in that inclusive window |
| `AllPermitCount` | All loaded application records assigned to the window |
| `FirstObservedApplication`, `LastObservedApplication` | Actual date extrema among records in that window |
| `ContextOnly` | Flags the open-ended early post-repeal window |

The provenance table records the snapshot filename, retrieval time, record count, and hashes of the snapshot, settings, and classification rules. These checks establish internal consistency and detect mismatched inputs. They do not independently audit the City's reporting completeness or freeze a changing API during pagination.

## 4. Profiling and cleaning

`DataProfiler` summarizes raw row/column counts, data types, missingness, permit-number uniqueness, duplicate examples, date ranges, and source category distributions. Missing percentages use all loaded records as their denominator. Raw `object` columns may contain strings or mixed values; they are not necessarily parsed dates.

`PermitCleaner` maps source names to analysis names, normalizes values, and records invalid-date and coordinate flags. The comparison table shows missing counts before and after cleaning; `change` is the after count minus the before count. Invalid flags distinguish unusable values from missing ones.

Assertions verify that cleaning preserves all 31,339 records and their index and does not mutate the raw table. Records are not silently deduplicated or dropped.

## 5. Classification and review evidence

The classifier applies ordered rules from `config/classification_rules.csv`. Winning rules determine housing type, residential inclusion, rezoning relevance, and review status. The notebook also retains evidence of other matching rules.

| Classification result | Recorded count |
|---|---:|
| Enabled rules | 34 |
| Records matching a rule | 31,329 |
| Unmatched records | 10 |
| Records requiring review | 2,635 |
| Records with overlapping matches | 29,798 |
| Included residential records | 14,277 |

`ClassificationRule` identifies the winning rule. `ClassificationMatchedRules` lists matching rules, while `ClassificationConflictCount` records additional matches. Broad fallback rules can overlap with more specific rules, so overlap is not automatically an incorrect result.

The notebook displays examples of unmatched, review, and overlapping records. The per-rule coverage table distinguishes `winning_records` from `all_matching_records`; a record can contribute to several rules' match counts. Those counts must not be added as though they represented unique applications.

Rule coverage measures whether rules matched, not whether classifications are correct. Rule validation labels are metadata, not an independent accuracy estimate. The run supplies no human-labelled reference column and does not perform an accuracy audit. Review flags do not automatically exclude a record when `IncludeResidential` remains true.

## 6. Period, season, and processing features

Application dates assign `Period`; decision dates separately determine `DecisionPeriod`. `CrossesPeriodBoundary` identifies assessable records whose application and decision periods differ. Missing values mean the crossing cannot be assessed. The recorded run found 1,679 crossings and 7,037 unassessable records.

Meteorological seasons are Winter (December–February), Spring (March–May), Summer (June–August), and Fall (September–November). Winter crosses calendar years; the heatmap assigns it to the January/February year. `IsCompleteSeason` and `IsPartialSeason` describe season exposure within a study window and observation horizon, not source-reporting completeness.

Processing duration is decision date minus application date in calendar days. Feature flags expose missing or invalid dates, negative durations, pending/right-censored proxies, and dates after the observation horizon. `FollowUpDays` records available follow-up according to the feature logic.

These early feature summaries cover **all permits**. The later processing analysis covers **included residential permits**. Flags can overlap and must not be summed into a count of unique problematic records. In particular, a missing decision date is an analytical pending proxy; it does not establish the City's official current status.

## 7. Validation reports

| Report | Purpose | Recorded outcome |
|---|---|---|
| `schema_report` | Checks required columns; extra columns are informational | 0 errors; 96 informational additional columns |
| `quality_report` | Checks identifiers, dates, durations, and geography | 7 pass, 3 warn, 0 fail |
| `classification_validation` | Checks rule references, audit consistency, and review coverage | Review warnings remain; human-label accuracy not assessed |

The quality warnings identify 7,037 missing decision dates, 54 missing communities, and 54 records with missing coordinates. Enabled checks detected no missing or duplicate permit identifiers, missing or invalid application dates, invalid decision dates, negative processing durations, or invalid coordinates.

Affected-row counts overlap. Optional minimum-row and freshness thresholds are not enabled in the current settings. Additional columns are expected because the workflow retains source evidence and adds features.

The validators return reports without changing records. A successfully executed notebook does not imply that every data-quality concern is resolved: report warnings and failures do not automatically halt this exploratory analysis.

## 8. Analysis tables and denominators

Six reusable analysis strategies produce 21 in-memory tables in `analysis_tables`.

| Analysis | Output keys | How to interpret them |
|---|---|---|
| Volume | `permit_volume`, `monthly_volume` | Residential counts, all-record denominators, exposure, monthly coverage, and primary-period changes |
| Housing type | `type_summary`, `type_period_totals` | Residential housing-type counts and shares with period denominators |
| Geography | `community_summary`, `ward_summary`, `geography_period_totals` | Community/ward counts, missing geography, and During-minus-Before comparisons |
| Processing | `processing_summary`, `processing_type_summary`, `processing_community_summary`, `processing_period_totals` | Eligible duration distributions and exclusions by period, type, and community |
| Rezoning relevance | `rezoning_summary`, `rezoning_by_type`, `rezoning_by_district`, `rezoning_by_rule` | Project-defined relevance counts/shares and review evidence |
| Seasons | `seasonal_summary`, `seasonal_monthly_volume`, `calendar_month_summary`, `complete_seasons`, `partial_seasons`, `unknown_seasons` | Seasonal counts, exposure, completeness, and supporting breakdowns |

Not every table is printed in full. The complete tables remain available in the kernel; for example, `analysis_tables["processing_type_summary"]`.

Key definitions:

| Measure | Definition / caution |
|---|---|
| `PermitCount` | Included residential application records |
| `AllPermitCount` | All application records in the relevant group |
| `ExcludedCount` | All records minus included residential records |
| `DP_Rate30` | `PermitCount / ExposureDays * 30`; applications per 30 exposed calendar days |
| `AbsoluteChange` | During count minus Before count in primary comparisons |
| `PercentChange` | Absolute change divided by Before count, multiplied by 100; undefined for zero baseline |
| Share fields | Generally fractions from 0 to 1; multiply by 100 to display a percentage |
| `SmallBaselineWarning` | Flags community/ward baselines below the configured threshold of 5 |

Repeated period denominators on type or geography rows must not be summed. Zero and missing values have different meanings. Mean/median monthly counts include boundary fragments and are not exposure-adjusted rates.

Assertions reconcile volume, monthly, seasonal, type, community, ward, and rezoning totals to the residential population and verify that analysis does not mutate its input.

## 9. Recorded residential findings

These results describe the pinned snapshot and rules used in the verified run. Rerun outputs take precedence after any input changes.

| Measure | Before | During | Early Post-Repeal: context only |
|---|---:|---:|---:|
| Residential applications | 7,940 | 6,038 | 299 |
| Applications per 30 exposed days | 325.85 | 248.82 | 169.25 |
| Valid processing durations | 6,505 | 4,436 | 44 |
| Ineligible processing durations | 1,435 | 1,602 | 255 |
| Median eligible processing days | 47 | 73 | 14 |
| Q1 / Q3 processing days | 32 / 86 | 40 / 124 | 6.5 / 30.25 |
| Processing IQR, days | 54 | 84 | 23.75 |
| Rezoning-relevant residential records | 7,433 | 5,575 | 279 |
| Rezoning-relevant share | 93.61% | 92.33% | 93.31% |
| Residential records flagged for classification review | 124 | 407 | 5 |

During contains 1,902 fewer included residential applications than Before, a count change of approximately **−23.95%**. The primary windows differ by three days, so inspect exposure-adjusted rates as well as counts. This is a descriptive association, not evidence that rezoning caused the difference.

Eligible-duration medians describe applications with usable decisions. They do not correct for censoring or unequal follow-up. Only 44 of 299 post-repeal residential records have eligible durations; its 14-day median must not be interpreted as an overall improvement in processing speed.

The rezoning-relevance flag is a project classification, not an official City designation. Community tables rank both increases and decreases, retaining small-baseline warnings and missing geography. Review those flags before interpreting percentage changes.

## 10. Reading the four charts

| Chart | Axes / panels | Displayed measure |
|---|---|---|
| Monthly line chart | Application month horizontally; period-specific series | Residential application count |
| Month × Year heatmap | Jan–Dec rows, calendar-year columns, separate policy-period panels | Residential application count |
| Season × Year heatmap | Winter–Fall rows, season-year columns, separate policy-period panels | Count by default; optional `DP_Rate30` |
| Season × Policy Period heatmap | Seasons in rows, policy periods in columns | Pooled `sum(PermitCount) / sum(ExposureDays) * 30` |

Partial months use special markers on the line chart and `*` annotations in the monthly heatmap. Gray/dash cells indicate unavailable or excluded coverage, not zero activity. The monthly heatmap can mark unknown coverage with `?`.

Boundary months are split between policy periods. For example, August 2024 contains 44 Before residential records for August 1–5 and 268 During records for August 6–31. August 2026 contains 12 During records for August 1–3 and 165 post-repeal records for August 4–31. A low boundary fragment is not a full-month collapse in activity.

Seasonal charts default to complete seasons. No complete post-repeal season is available at the recorded horizon, so its seasonal cells are gray even though 299 residential records exist. Enable partial seasons deliberately to include those fragments. Pooled seasonal rates use summed counts and exposure, not an unweighted average of rates. Exposure adjustment does not remove confounding or reporting lag.

All four figures rendered successfully and were visually reviewed. They are embedded as notebook outputs using PNG buffers. Optional exports can also save them as external PNG files.

## Optional exploratory exports

Excel layout is controlled by `storage.excel_layout` when `xlsx` is included in
`storage.processed_output_formats`: `one_file_per_table` writes separate workbooks;
`one_workbook` writes `complete_period_exploration_workbook.xlsx` with one table
per sheet (27 sheets for this notebook). CSV and other selected formats continue
to use separate table files. Reload configuration after changing YAML, and restart
the kernel after updating the package code. The default layout is separate files.

The notebook's `## Optional exploratory exports` section follows the charts. Run the preceding analysis and chart cells first, then set `EXPORT_EXPLORATORY_OUTPUTS=True` and execute the export cell to save the featured permit table, all 21 analysis tables, three validation reports, reconciliation totals, a bias audit, and four PNG charts.

Each enabled run uses a unique directory under `reports/notebook_complete_period/`, containing `tables/` and `figures/`. Table formats and labels come from project settings; the current table format is CSV. Table overwrite is disabled, and separate run directories preserve earlier chart exports. The displayed output-path table lists the generated files.

The default is `EXPORT_EXPLORATORY_OUTPUTS=False`, which writes no export files. Return the flag to `False` after an intentional export if subsequent runs should remain display-only. Exports remain exploratory: they preserve validation findings and do not establish classification accuracy, source completeness, or agreement with a Power BI report. Export writes are per file, so a failed export may leave some files in its run directory.

## 11. Verification and remaining limitations

The original 15 analysis and chart code cells executed successfully in order against the pinned snapshot, including checksum/query checks, preserved-input assertions, reconciliation checks, and chart generation. The added optional export cell brings the notebook to 16 code cells. This was a notebook execution check; it was not a new full project test-suite run or an independent audit of source completeness.

Before using the exploration in final reporting, resolve or explain classification review records and missing fields, assess reporting lag and processing follow-up, and examine reasonable alternative classification assumptions. The early post-repeal period remains short and incomplete. Interest rates, population, housing demand, costs, seasonality, and other changes can also affect observed activity.

Study-specific sensitivity analyses, independent classification accuracy review, minimum-follow-up eligibility, automatic stopping on failed validation, and Power BI reconciliation remain outside this notebook's completed workflow.

## Related project files

- [Notebook](02_complete_period_exploration.ipynb)
- [Before-only notebook guide](01_permit_exploration_explaination.md)
- [Settings](../config/settings.yaml)
- [Classification rules](../config/classification_rules.csv)
- [Methodology](../docs/METHODOLOGY.md)
- [Bias and mitigation](../docs/BIAS_AND_MITIGATION.md)
- [Configuration guide](../docs/CONFIGURATION.md)
- [Design patterns](../docs/DESIGN_PATTERNS.md)
