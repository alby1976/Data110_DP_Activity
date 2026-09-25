# Testing Framework

## Purpose

The project uses behavior-first automated tests to define what each Python module must do before its pseudocode is replaced with working code. Tests protect the analytical definitions as well as the software: a function is not complete merely because it runs; it must preserve configured study periods, cross-year winters, classification audit fields, valid denominators, and data-quality warnings.

The framework uses `pytest`. Test inputs are deliberately small pandas DataFrames so failures can be understood without downloading the full City dataset. External services, files, and pipeline collaborators should be replaced with temporary files, monkeypatches, or small stubs in unit tests.

## Current baseline

There is one corresponding test module for each non-`__init__` module under `src/dp_activity`. On September 24, 2026, `python -m pytest -q --basetemp=.pytest_cache/cli-smoke-full` with the configured Python 3.13.14 environment reports:

```text
522 passed
```

The project-default test requires `"csv" in config.raw_snapshot_formats`, allowing additional raw formats such as the committed Parquet option. The processed-output expectation remains CSV-only. There are no unexpected failures in this run.

Passing tests cover configuration behavior, CLI dispatch and downloads, log archiving, Socrata and file-format adapters, repositories, cleaning, profiling, classification, all three validators, the abstract analysis contract, and pipeline orchestration with injected collaborators. Offline CLI smoke tests additionally verify the complete table workflow with real collaborators and frozen synthetic data, not production-data validity.

No scaffold-related expected failures remain. Chart creation and saving have 40
passing tests, including real PNG/SVG/PDF rendering, missing-month gaps, explicit
boundary annotations, partial/unknown exposure markers, empty data, input
preservation, and invalid values. A rendered fixture was also visually inspected.
Heatmap tests additionally verify separate boundary-month fragments, a shared
color scale, missing-versus-zero cells, partial/unknown labels, empty and all-zero
data, and real PNG/SVG/PDF output. A rendered heatmap fixture was visually checked.
Seasonal heatmap tests verify the agreed row/column orientation, winter ending-year
labels, complete-season defaults, marked partial-season inclusion, missing exposure,
and pooled policy-period rates from unequal exposures. All three heatmap layouts
were visually inspected using synthetic fixtures.
Matplotlib 3.10.8 emits 143 NumPy 2.5.3 deprecation warnings from its date conversion
code in this environment; these are upstream warnings, not test failures.

The completed validator test modules contain 16 schema tests, 19 data-quality
tests, and 23 classification-validation tests. They cover input preservation,
configuration errors, immutable results, missing prerequisites, date and
coordinate edge cases, audit consistency, intentional rule overlap, and optional
independent human-label comparisons. Their tests now call the implementations
directly rather than using the scaffold-aware `implemented()` helper.

The implemented feature modules now have 12 period, 12 season, and 9 processing tests.
They cover calendar boundaries, cross-year/leap-year seasons, partial exposure,
explicit observation horizons, signed durations, invalid evidence, nullable
outputs, and input preservation. CLI tests check configured dependency wiring.

Four frozen-fixture CLI smoke cases now pass with real pipeline collaborators.
Study-specific sensitivity scenarios, run provenance, fatal-validation policy,
and CLI chart generation remain integration work despite the passing unit suite.

Geography tests cover community and ward counts, zero and small baselines, missing geography denominators, contextual periods, empty inputs, invalid schemas/configuration, and input preservation. CLI tests verify configured study labels and cleaner field names. An isolated temporary directory avoids a permissions error in the shared pytest temporary-folder cleanup.

## Installation and commands

On September 24, 2026, the exploratory notebook completed all 16 code cells from
a fresh kernel against its pinned 16,637-record Before snapshot. Five analysis
strategies reconcile to 7,940 residential records; the monthly line chart and
three heatmaps render successfully and were visually reviewed. Only Before
coverage is supplied. All-permit validation reports retain three quality warnings
and no failures. External exports were disabled; the optional enabled export
branch was not exercised during this notebook verification.

The separate [complete-period notebook](../notebooks/02_complete_period_exploration.ipynb)
was verified against `development_permits_20260925_045241.parquet`: 31,339 raw
records across all three configured periods, including 14,277 residential records.
All 15 setup, analysis, and chart code cells executed in order; six strategies
produced 21 tables, and all four charts rendered and were visually reviewed.
Assertions checked checksum/query identity, coverage, input preservation, and
residential-count reconciliation. Quality validation reported 7 passes, 3 warnings,
and no failures; 2,635 classifications require review.

The added optional export cell brings that notebook to 16 code cells. Its default
`EXPORT_EXPLORATORY_OUTPUTS=False` branch executed successfully without writing
table or chart files. The enabled branch, which writes to a unique directory under
`reports/notebook_complete_period/`, was not run in this verification. Existing
exporter unit tests are separate evidence and do not verify this enabled notebook
branch against the complete-period snapshot. This notebook work did not rerun or
change the recorded full-suite baseline. See the
[companion guide](../notebooks/02_complete_period_exploration_explanation.md)
for the snapshot dates, results, and interpretation limits.

The exporter has 17 passing tests covering clean/analysis/validator outputs,
independent residential denominators, missing audit evidence, empty tables,
CSV/JSON/Parquet round trips, one shared timestamp, overwrite protection, invalid
schemas, and pre-write filename collision checks. CLI tests verify configured
output-label wiring. These tests do not establish full-run provenance or actual
Power BI reconciliation.

Sensitivity analysis has 20 passing tests for named alternatives, explicit
references, signed and percentage changes, missing/zero baselines, input-copy
isolation, invalid configurations/results, and visible scenario failures.
Classification-review and complete-season fixtures demonstrate injected policies;
the CLI's empty scenario mapping does not yet execute study sensitivity checks.

CLI cutoff tests cover UTC date conversion, explicit overrides, missing and
malformed metadata, invalid dates, and dependency wiring. A real feature/analysis
integration test verifies that the frozen cutoff censors later decisions and
gives matching partial-season/month exposure and DP_Rate30 values. This bypasses
the unfinished exporter and does not establish a complete pipeline smoke test.

DP_Rate30 checks cover a single inclusive day, leap-year month exposure, partial
months and seasons, residential-only counts, zero activity, unknown exposure,
and pooled like-month rates. Existing input-preservation assertions continue to
verify that deriving the rate does not modify source records.

Seasonal tests verify complete/partial/unknown partitioning, cross-year leap
winter, policy-boundary splits, configured zero-activity seasons, like-month
exposure counts, processing eligibility, empty inputs, invalid identities, and
contradictory completeness flags. The original scaffold test now calls the
implementation directly. CLI tests verify windows, season definitions, and the
application-date field. Rezoning analysis now has 15 passing tests covering
residential denominators, unknown and review counts, audit breakdowns, empty
tables, invalid inputs, and input preservation.

Processing analysis tests verify exact means, medians, linearly interpolated
quartiles and IQR, residential denominators, pending/censoring counts, optional
audits, empty cohorts, missing subgroup labels, and input preservation. Integration
with the real processing feature filter checks observation cutoffs and configured
minimum days. Malformed flags, contradictory eligibility, nonfinite durations,
and schema/configuration errors are rejected. The scaffold test now calls the
implementation directly; CLI tests verify configured period ordering.

From the repository root, create and activate a virtual environment, then install the pinned testing dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the complete suite:

```bash
python -m pytest -q
```

Run one test file while implementing a module:

```bash
python -m pytest tests/features/test_season_features.py -v
```

Run one named test:

```bash
python -m pytest tests/features/test_season_features.py::test_cross_year_winter_uses_december_start -v
```

Stop after the first unexpected failure:

```bash
python -m pytest -x
```

## Result meanings

| Result | Meaning | Required response |
|---|---|---|
| `.` / `PASSED` | Implemented behavior met its assertions | Continue; retain the regression test |
| `XFAIL` | The target still raised `NotImplementedError` | Implement that module when it reaches the timeline |
| `F` / `FAILED` | Code ran but produced the wrong behavior | Fix the implementation or, if the requirement changed, update the documented rule and test together |
| `E` / `ERROR` | Test setup, import, fixture, or execution failed | Fix the test environment or underlying exception before interpreting results |
| `XPASS` | A test marked as expected to fail unexpectedly passed | Investigate and remove stale expected-failure handling |

`XFAIL` must never be counted as a passed analytical check. The final project should have no scaffold-related expected failures.

## Test organization

The test tree mirrors the source tree:

```text
src/dp_activity/features/season_features.py
tests/features/test_season_features.py
```

| Area | Main behaviors protected |
|---|---|
| CLI and configuration | command parsing, required settings, path resolution, non-overlapping periods, storage-format settings, log archiving |
| Socrata and repositories | retrieval metadata, deterministic persistence, configured formats, no accidental index columns or unintended overwrites |
| Cleaning | explicit name mapping, text normalization, date parsing, no input mutation |
| Classification | rule parsing, priority, first-match behavior, audit fields, unmatched and conflicting rules |
| Features | inclusive policy boundaries, cross-year winters, partial seasons, valid and pending processing times |
| Validation and profiling | missing schema, duplicate identifiers, freshness, missingness, rule coverage, review counts |
| Analysis | zero months, counts and shares, small baselines, valid denominators, censoring, sensitivity scenarios |
| Visualization and export | required columns, stable files, ISO dates, reconciliation outputs |
| Pipeline | stage order, dependency boundaries, named outputs, manifest-ready results |

## Implementation workflow

Use a small red–green–refactor cycle for one module at a time:

1. Open the source module and its matching test file.
2. Read the pseudocode and test assertions aloud before changing code.
3. Run only that test file and confirm it is currently `XFAIL` because of `NotImplementedError`.
4. Implement the smallest behavior needed to satisfy the test without hard-coding the example values.
5. Run the focused test until it passes.
6. Add boundary, missing-value, and invalid-input cases relevant to that module.
7. Run the entire suite to catch effects on other modules.
8. Refactor only while the suite remains green.
9. Commit the source and its tests together with a message describing the behavior implemented.

Do not change an assertion merely to make a failure disappear. If an analytical definition changes, update the applicable documentation, configuration, implementation, and tests in the same change so the decision remains auditable.

## Required test layers

### Unit tests

Unit tests cover one function or class with tiny controlled inputs. These tests should make up most of the suite and should not require network access.

### Integration tests

Integration tests will verify adjacent components together, including configuration → cleaning → classification → features, and analysis tables → Power BI exports. They should use a small frozen fixture derived from the source schema rather than the full live dataset.

### Data-contract tests

Data-contract tests will verify required City API fields, supported types, rule-file columns, output schemas, unique keys, and allowed categorical values. Live-source checks must be kept separate from offline reproducibility tests because the public dataset can change.

### Reconciliation tests

Before submission, Python headline totals must be compared with the corresponding Power BI measures. Reconciliation should cover residential record count, period totals, monthly totals, classification totals, valid processing-time count, and missing/review counts.

### End-to-end smoke test

Run `python -m pytest tests/test_cli_smoke.py -q`. The versioned synthetic fixture
is documented in [tests/fixtures/cli_smoke/README.md](../tests/fixtures/cli_smoke/README.md).
Tests copy settings, committed classification rules, and the snapshot into isolated
temporary directories, prohibit network connections, and invoke `cli.main` with
real repositories, cleaning, classification, features, validators, analyses, and
exporter. CSV, JSON, and Parquet cases verify policy boundaries, totals, zero
months, rates, censoring, audit reports, log archiving, and repeat-run overwrite
behavior. Parquet is skipped only if its optional engine is unavailable.

A fourth case confirms current collect-only validation: duplicate identifiers
produce a failure report but do not prevent export or CLI success. This limitation
must remain visible until a fatal-validation policy is implemented. The tests
exercise CLI dispatch in-process; they do not validate shell installation,
production data, chart generation, sensitivity policy, Power BI measures, or run
manifest contents. Extend them as those integration stages are added.

## Test-data rules

- Use synthetic records for ordinary unit tests.
- Do not commit private, personal, or restricted data.
- A retained public-data fixture should be small, documented, and traceable to a source snapshot.
- Include dates exactly on August 5–6, 2024 and August 3–4, 2026.
- Include December, January, and February records to test one cross-year winter.
- Include missing dates, negative processing duration, pending applications, missing geography, duplicate identifiers, an unmatched classification, and a multi-rule conflict.
- Include a zero-baseline community so percentage-change handling is tested explicitly.

## Completion gates

A module is complete when:

- its matching scaffold test no longer reports `XFAIL`;
- its normal, boundary, missing-value, and invalid-input cases pass;
- related documentation and configuration agree with its behavior; and
- the complete suite still passes.

The Python analysis is ready for final Power BI reconciliation only when all scaffold-related `XFAIL` results have been removed, the frozen-snapshot integration test passes, and exported totals reconcile with Python results. Continuous integration is not configured yet; until it is added, the full suite must be run locally before each implementation commit and before submission.
