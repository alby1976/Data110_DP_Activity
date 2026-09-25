# Implementation Plan to October 12, 2026

## Purpose

This plan defines the work needed to move the project from the current scaffolded
baseline to a reproducible analysis package by October 12, 2026. The September 23
baseline is `522 passed`, with no unexpected failures; see
[Testing Framework](TESTING.md#current-baseline).

Configuration, downloads, adapters, repositories, cleaning, profiling, classification,
all three validators, CLI dispatch, log archiving, and pipeline orchestration are implemented.
Period, season, and processing feature filters are also implemented.
Volume, type, geography, processing-time, seasonal, rezoning, and the injected
sensitivity runner are implemented. Power BI table export is implemented; charts
are implemented as a Python API, with CLI integration pending. The timeline and
sprint tables below retain the original delivery plan; they are planning checklists,
not a record that every listed implementation step is still outstanding. A complete
table run with real collaborators now passes the frozen synthetic CLI smoke test.
Final study execution still needs the integration and validation policies below.

The plan prioritizes the executable Python pipeline first, then validation, analysis
outputs, Power BI readiness, and final reproducibility checks. The final deadline is
Monday, October 12, 2026.

## Success Criteria

### Current implementation checkpoint: September 23

All three validators are implemented and tested. Schema validation returns
immutable issues, data-quality validation returns immutable check results, and
classification validation returns a summary table with optional labelled-sample
confusion rows. The pipeline currently collects findings without stopping on
failed result statuses; an explicit fatal-finding policy remains an integration
decision before final outputs are accepted.

Remaining Python work, in implementation order:

1. Configure study-specific sensitivity scenarios using the implemented runner;
   the CLI currently supplies an empty scenario mapping.
2. Assemble complete run provenance and connect it to final outputs. Power BI
   table exports, validation/bias-audit/reconciliation tables, and configured
   naming/formats are implemented; manifest persistence exists separately.
3. Integrate the implemented chart factory into the reporting workflow with
   configured policy boundaries and chart destinations; the CLI does not call it yet.
4. Extend the passing frozen-fixture CLI smoke test as provenance, chart output,
   and fatal-validation policy are integrated. CSV/JSON/Parquet tables, log
   archiving, repeated-run overwrite behavior, and collect-only validation are verified.

Rezoning analysis is complete: period counts and shares use all residential permits
as the denominator, with unknown relevance, overlapping review audits, and optional
rule/type/district breakdowns. The sensitivity runner and 20 focused tests are
complete. The exporter has 17 passing tests and the chart factory has 40.
No scaffold XFAILs remain. Four offline CLI smoke cases now pass with real
collaborators and frozen synthetic data; study-specific sensitivity definitions
remain integration work.
All three feature filters are pure,
input-preserving transformations with boundary and invalid-input tests. The CLI
binds configured period boundaries, season display labels, processing date fields,
and minimum processing days. The CLI now resolves the snapshot retrieval date in
UTC (or an explicit `--observation-end` override) and passes the same cutoff to
season/processing features and volume/seasonal analyses. Pending flags are
analytical proxies, and minimum-follow-up eligibility remains a planned policy.
The exploratory notebook now executes all three feature filters before validation, using the snapshot retrieval date in UTC as its observation horizon.

The Before exploratory notebook now runs all three validators, five residential
analysis strategies, the monthly line chart, and three heatmaps. All 16 code cells
passed in a fresh kernel on September 24, reconciling 7,940 residential records.
Only the verified Before window enters analyses; other periods are not invented
as zeros. Notebook exports are disabled by default. There were no schema errors
or classification audit inconsistencies.
Warnings include missing decisions/geography and unmatched/review classifications.
See the [notebook explanation](../notebooks/01_permit_exploration_explaination.md#recorded-before-snapshot-validation-results)
for counts. Manual warning investigation and independent human-label review remain
follow-up work before final analysis.

### Complete-period exploratory checkpoint

The [complete-period notebook](../notebooks/02_complete_period_exploration.ipynb)
now uses a separate 31,339-record snapshot covering Before, During, and Early
Post-Repeal. Its six analysis strategies include geography comparisons and produce
21 tables reconciling to 14,277 residential records. All 15 original code cells
executed successfully and four charts were visually reviewed. The additional
optional export cell was verified with exports disabled; its enabled branch has
not been exercised against this snapshot.

Optional exports use the existing exporter and chart API, creating a unique run
directory under `reports/notebook_complete_period/` with configured table formats
and PNG figures. This notebook workflow does not complete CLI chart integration,
full run provenance, final validation acceptance, or Power BI reconciliation.
The post-repeal window is contextual and source/classification warnings still
need review. See the
[complete-period guide](../notebooks/02_complete_period_exploration_explanation.md)
for coverage, output definitions, and recorded findings.

### Final acceptance criteria

The project is complete when:

- all scaffold-related `XFAIL` tests have been removed or converted to normal passing
  tests;
- the CLI can run one configured workflow from a frozen raw snapshot;
- raw and processed outputs respect `config/settings.yaml` storage formats, basename,
  overwrite behavior, and log archiving;
- classification rules are loaded, validated, applied, and audited;
- cleaned, classified, feature-enriched permit data can be exported for Power BI;
- monthly, seasonal, type, geography, processing-time, rezoning, sensitivity, validation,
  and bias-audit outputs are generated;
- a small frozen fixture or snapshot supports offline smoke testing;
- Python headline totals reconcile with Power BI measures; and
- the README, methodology, data dictionary, configuration guide, and final report agree.

## Critical Path

1. Implement data access and persistence boundaries.
2. Implement cleaning, classification, and feature stages.
3. Implement pipeline orchestration.
4. Implement analyses and validation reports.
5. Export stable output tables and a manifest.
6. Build Power BI model/dashboard from generated outputs.
7. Reconcile, document findings, and freeze the final run.

## Timeline

| Date | Milestone | Deliverables | Exit Check |
|---|---|---|---|
| Sep 18 | Planning lock | This implementation plan; confirmed config expectations | Plan committed and linked from README |
| Sep 19, Sep 21 | Data access and repositories | `SocrataAdapter`, `RawDataRepository`, `OutputRepository`; CSV/Parquet save/load behavior | Adapter and repository tests pass |
| Sep 20 | Sunday break | Day off for rest and recovery | No project work scheduled |
| Sep 22 | Configuration-to-pipeline wiring | CLI uses config storage/logging settings; snapshot paths and output paths are deterministic | CLI and repository integration tests pass |
| Sep 23-24 | Cleaning and profiling | `PermitCleaner`, `DataProfiler`; source-field mapping, date parsing, text normalization, profile tables | Cleaning/profiling tests pass |
| Sep 25-26 | Classification foundation | `ClassificationRule.matches()`, `RuleLoader`, `PermitClassifier`; rule coverage report | Rule/classifier tests pass |
| Sep 27 | Sunday break | Day off for rest and recovery | No project work scheduled |
| Sep 28 | Validation foundation | Schema, data-quality, and classification validators | Validation tests pass |
| Sep 29-30 | Feature engineering | Period, season, and processing-time features | Feature tests pass, boundary dates verified |
| Oct 1 | Analysis tables | Volume, type, geography, processing, rezoning, seasonal, and sensitivity analyses | Analysis tests pass |
| Oct 2 | Pipeline orchestration | `AnalysisPipeline.__init__()` and `run()` integrate stages and collect results | Pipeline test passes |
| Oct 3 | Export and manifest | `PowerBIExporter`, output schemas, reconciliation table, run manifest | Export tests pass |
| Oct 4 | Sunday break | Day off for rest and recovery | No project work scheduled |
| Oct 5 | End-to-end smoke test | Small frozen fixture, CLI run, generated outputs in configured formats | Smoke test passes locally |
| Oct 6 | Data pull and rule review | Real source snapshot, profile review, classification-rule adjustments with notes | Rule coverage and unmatched counts reviewed |
| Oct 7-8 | Power BI build | Model, measures, dashboard pages, slicers, reconciliation checks | Power BI totals match Python outputs |
| Oct 9 | Interpretation and bias audit | Findings, limitations, sensitivity results, bias-control documentation | Results are traceable to snapshot/config |
| Oct 10 | Final documentation pass and freeze candidate | README commands, methodology, data dictionary, references, presentation notes; fresh clone/setup check, full tests, smoke test, final Power BI export | Docs match generated outputs and no unexpected failures remain |
| Oct 11 | Sunday break | Day off for rest and recovery | No project work scheduled |
| Oct 12 | Submission package | Final report, presentation/dashboard assets, archived log, manifest, reproducibility notes | Submission-ready package complete |

## Work Breakdown

### 1. Data Access and Persistence

- Implement Socrata pagination with `$limit`, `$offset`, and stable ordering.
- Add request timeout, retry policy, app-token header support, JSON-list validation, and
  page-size validation.
- Save immutable raw snapshots with metadata and checksums.
- Load snapshots from supported CSV and Parquet formats.
- Implement output writes with atomic replacement when `overwrite_outputs` is true.
- Reject accidental overwrite or choose a documented collision-safe path when
  `overwrite_outputs` is false.

### 2. Cleaning and Profiling

- Normalize City API field names to project-standard names.
- Preserve source evidence fields beside cleaned fields.
- Trim text, convert blank strings to missing values, and parse dates explicitly.
- Convert coordinates without inventing values.
- Produce profiling outputs for row counts, missingness, date ranges, duplicates, and
  categorical value counts.

### 3. Classification

- Parse and validate `config/classification_rules.csv`.
- Implement exact, contains, starts-with, and regex matching.
- Apply enabled rules in `(Priority, RuleID)` order.
- Record first match, validation status, residential inclusion, type, rezoning relevance,
  review flags, unmatched records, and conflicts.
- Retain rule coverage tables for audit and reporting.

### 4. Features and Validation

- Assign study periods from `AppliedDate`, including boundary dates.
- Add cross-year meteorological seasons and complete-season flags.
- Add processing-time validity, pending, negative-duration, and right-censoring flags.
- Validate source and processed schemas.
- Report duplicate identifiers, missing geography, stale data, invalid dates, and
  classification coverage.

### 5. Analysis and Export

- Produce monthly and total volume outputs with explicit zero months.
- Produce development-type shares using all residential records as denominators.
- Produce geography outputs with small-baseline warnings.
- Produce processing-time summaries using only valid durations while reporting excluded
  rows.
- Produce rezoning-relevance and seasonal outputs with clear denominators.
- Produce sensitivity outputs for alternate date/classification/complete-period rules.
- Export clean permits, summaries, validation reports, bias audit, reconciliation table,
  and manifest.

### 6. Power BI and Final Reporting

- Import generated outputs into Power BI.
- Define measures from exported stable columns, not independent duplicated logic.
- Reconcile total residential permits, period counts, monthly counts, type counts,
  processing valid counts, and review/missing counts.
- Build dashboard pages for overview, time trend, geography, type mix, processing time,
  rezoning relevance, and limitations.
- Write final interpretation using observational language only.

## Short Sprint Backlog

Each sprint should be small enough to complete in 15 minutes or less. Use CLI for
repeatable implementation, tests, exports, and final outputs. Use Jupyter only for
temporary data inspection, profiling review, classification-rule exploration, and visual
sanity checks that will later be converted into source code, tests, or documented rules.

| Sprint | Step | Suggested Surface | Done When |
|---|---|---|---|
| 1 | Run `python -m pytest -q` and save the current pass/XFAIL count in notes | CLI | Baseline is known before coding |
| 2 | Open one target source file and its matching test file | CLI | The exact failing scaffold is identified |
| 3 | Run the single target test file | CLI | It reports expected `XFAIL` before implementation |
| 4 | Replace one `NotImplementedError` with the smallest working behavior | CLI | Focused test no longer XFAILs |
| 5 | Add one boundary or invalid-input test for the behavior just implemented | CLI | New test fails before the fix or passes after the fix |
| 6 | Run the focused test file again | CLI | Focused file passes or has only unrelated expected XFAILs |
| 7 | Run the full suite | CLI | No unexpected failures were introduced |
| 8 | Update the relevant doc sentence if behavior changed | CLI | Docs and implementation agree |
| 9 | Inspect `config/settings.yaml` before changing pipeline wiring | CLI | The setting being used is confirmed |
| 10 | Review actual City source field names and example values | Jupyter | Candidate field map or rule update is noted |
| 11 | Convert any useful notebook finding into a test or config/rule change | CLI | No project behavior depends only on notebook state |

### Data Access and Repository Sprints

| Sprint | Step | Suggested Surface | Done When |
|---|---|---|---|
| 12 | Add page-size validation cases for `SocrataAdapter.iter_records()` | CLI | Invalid page sizes have tests |
| 13 | Implement Socrata query parameter construction | CLI | Test verifies `$limit`, `$offset`, and filters |
| 14 | Stub one successful Socrata page response | CLI | Adapter yields records from mocked JSON |
| 15 | Stub an empty second page | CLI | Adapter stops cleanly after the last page |
| 16 | Stub malformed non-list JSON | CLI | Adapter raises a clear error |
| 17 | Implement `download()` metadata fields | CLI | Dataset ID, row count, endpoint, timestamp, query are populated |
| 18 | Add a raw repository CSV save/load test | CLI | Round trip preserves sample records |
| 19 | Add a raw repository Parquet save/load test guarded by dependency availability | CLI | Parquet behavior is tested or skipped clearly |
| 20 | Add checksum sidecar expectations | CLI | Snapshot metadata records file checksum |
| 21 | Implement overwrite protection for immutable raw snapshots | CLI | Existing snapshots are not replaced |
| 22 | Implement `OutputRepository.write_table()` for CSV | CLI | Output has no implicit index column |
| 23 | Implement output overwrite behavior from config | CLI | Existing output is replaced or preserved as configured |
| 24 | Implement manifest writing | CLI | Manifest JSON is stable and readable |

### Cleaning, Profiling, and Classification Sprints

| Sprint | Step | Suggested Surface | Done When |
|---|---|---|---|
| 25 | Inspect distinct source categories and proposed-use values from a small sample | Jupyter | Candidate classification values are listed |
| 26 | Add cleaner test for column renaming | CLI | City field names map to project names |
| 27 | Implement cleaner copy behavior | CLI | Input object is not mutated |
| 28 | Implement text trimming and blank-to-missing conversion | CLI | Empty strings become missing values |
| 29 | Implement configured date parsing | CLI | Valid, invalid, and missing dates are flagged correctly |
| 30 | Implement coordinate numeric conversion | CLI | Bad coordinates are missing, not guessed |
| 31 | Add profiler missingness test | CLI | Missing counts and percentages are returned |
| 32 | Add profiler duplicate permit test | CLI | Duplicate identifiers are reported |
| 33 | Implement `ClassificationRule.matches()` exact and contains modes | CLI | Case-insensitive match test passes |
| 34 | Implement starts-with and regex matching | CLI | Supported match modes pass focused tests |
| 35 | Add rule-loader required-column test | CLI | Missing rule-file columns raise a clear error |
| 36 | Implement strict Boolean parsing in rule loader | CLI | `TRUE` and `FALSE` parse predictably |
| 37 | Implement rule ordering by priority and rule ID | CLI | Enabled rules are sorted deterministically |
| 38 | Implement first-match classifier behavior | CLI | First matching rule is recorded |
| 39 | Implement unmatched `Review` behavior | CLI | Unmatched rows remain auditable |
| 40 | Review unmatched or provisional records from a sample | Jupyter | Rule changes are justified with notes |
| 41 | Convert rule-review decisions into `classification_rules.csv` updates | CLI | Rule file remains versioned and testable |

### Feature and Validation Sprints

| Sprint | Step | Suggested Surface | Done When |
|---|---|---|---|
| 42 | Add period boundary examples for Aug 5/6, 2024 and Aug 3/4, 2026 | CLI | Boundary tests cover all policy cutoffs |
| 43 | Implement period assignment | CLI | Period test passes |
| 44 | Add season examples for Dec/Jan/Feb | CLI | Cross-year winter test is explicit |
| 45 | Implement season start and label logic | CLI | Winter labels sort correctly |
| 46 | Add partial-season examples around policy boundaries | CLI | Partial seasons are flagged |
| 47 | Add processing-days examples for valid, negative, missing decision | CLI | Duration edge cases are tested |
| 48 | Implement processing flags | CLI | Valid/pending/negative flags pass |
| 49 | Implement schema missing-column report | CLI | Missing required columns are errors |
| 50 | Implement duplicate permit quality check | CLI | Duplicate count is reported |
| 51 | Implement missing geography quality check | CLI | Missing community/coordinates are warnings |
| 52 | Implement classification coverage validation | CLI | Unmatched/review counts are reported |
| 53 | Review validation output on a sample snapshot | Jupyter | Warnings are understandable and actionable |

### Analysis and Export Sprints

| Sprint | Step | Suggested Surface | Done When |
|---|---|---|---|
| 54 | Add zero-month fixture for volume analysis | CLI | Empty months appear in output |
| 55 | Implement monthly and total volume tables | CLI | Volume tests pass |
| 56 | Add development-type denominator test | CLI | Type share uses all residential permits |
| 57 | Implement type summary | CLI | Type analysis test passes |
| 58 | Add geography small-baseline fixture | CLI | Small communities are flagged, not removed |
| 59 | Implement geography summary | CLI | Geography test passes |
| 60 | Add processing summary fixture | CLI | Invalid rows are excluded but counted |
| 61 | Implement processing summary | CLI | Processing test passes |
| 62 | Add rezoning denominator fixture | CLI | Rezoning share denominator is explicit |
| 63 | Implement rezoning summary | CLI | Rezoning test passes |
| 64 | Add complete/partial seasonal fixture | CLI | Seasonal headline excludes partial seasons |
| 65 | Implement seasonal summary | CLI | Seasonal test passes |
| 66 | Add one sensitivity scenario fixture | CLI | Scenario outputs are retained |
| 67 | Implement sensitivity summary | CLI | Sensitivity test passes |
| 68 | Inspect analysis tables for obvious outliers | Jupyter | Any anomaly is traced to data or code |
| 69 | Implement Power BI CSV export schemas | CLI | Export tests pass |
| 70 | Add configured-format export test | CLI | CSV and Parquet settings are respected |
| 71 | Implement reconciliation table | CLI | Python headline totals are exported |

### Pipeline, Smoke Test, and Reporting Sprints

| Sprint | Step | Suggested Surface | Done When |
|---|---|---|---|
| 72 | Store injected collaborators in `AnalysisPipeline.__init__()` | CLI | Constructor test passes |
| 73 | Implement first pipeline stage: load snapshot | CLI | Pipeline can read stub repository output |
| 74 | Add cleaning and classification calls to pipeline | CLI | Stage order is tested |
| 75 | Add feature-builder loop to pipeline | CLI | Feature builders run in order |
| 76 | Add validator loop to pipeline | CLI | Validation reports are collected |
| 77 | Add analysis loop to pipeline | CLI | Analysis tables are collected by name |
| 78 | Add export call and result object | CLI | Pipeline returns output paths |
| 79 | Run CLI with a tiny frozen fixture | CLI | Smoke test produces configured outputs |
| 80 | Inspect generated CSV/Parquet files | Jupyter | Output columns and row counts look plausible |
| 81 | Create final real Socrata snapshot | CLI | Snapshot and metadata are saved |
| 82 | Profile real snapshot and review distinct values | Jupyter | Rule updates and cautions are identified |
| 83 | Run final pipeline from frozen snapshot | CLI | Outputs, manifest, and archived log are created |
| 84 | Import outputs into Power BI | Power BI Desktop | Model loads without manual data edits |
| 85 | Reconcile Python totals with Power BI measures | Power BI Desktop and CLI | Differences are zero or explained |
| 86 | Draft results narrative from generated tables | CLI | Report language matches outputs |
| 87 | Update README run commands after smoke test | CLI | Commands work from the repository root |
| 88 | Run full suite and record final count | CLI | No unexpected failures remain |
| 89 | Archive final run artifacts | CLI | Final log, manifest, and outputs are preserved |

## Daily Operating Rules

- Keep Sundays as planned days off. Use September 20, September 27, October 4, and
  October 11, 2026 for rest rather than project work.
- Implement one module or one closely related module group at a time.
- Run the focused test first, then the full suite before closing the day.
- Remove each `XFAIL` only when the behavior is implemented and assertions pass normally.
- Update docs and tests in the same change when analytical behavior changes.
- Keep raw source snapshots out of Git unless a deliberately small fixture is created.
- Preserve existing design patterns: adapters for external formats, repositories for
  persistence, strategies for analyses/validators, and CLI as the composition root.

## Risk Controls

| Risk | Mitigation |
|---|---|
| Too many scaffolded modules remain late in the schedule | Prioritize the executable pipeline and core tables before visualization polish |
| Live Socrata data changes during development | Use a frozen snapshot for repeatable tests and final Power BI reconciliation |
| Classification rules remain ambiguous | Preserve `Review`, unmatched counts, validation status, and sensitivity outputs |
| Parquet dependency is unavailable | Keep CSV enabled as the default storage format |
| Power BI logic drifts from Python | Export reconciliation tables and build measures from generated columns |
| Log/output files are overwritten during repeated runs | Use configured log archiving and `overwrite_outputs` behavior |

## Final Week Checklist

- [ ] Full test suite has no unexpected failures.
- [ ] Scaffold-related `XFAIL` results are resolved or explicitly documented as out of
  scope.
- [x] CLI table smoke test runs from a frozen synthetic snapshot.
- [ ] Generated outputs match configured storage formats.
- [ ] Pipeline log is archived for the final run.
- [ ] Manifest records snapshot, config, rule file, checksums, and output paths.
- [ ] Power BI totals reconcile with Python outputs.
- [ ] Final report includes limitations, bias controls, and sensitivity results.
- [ ] README setup and run commands have been tested from a clean environment.
