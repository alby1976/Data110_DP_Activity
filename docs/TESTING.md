# Testing Framework

## Purpose

The project uses behavior-first automated tests to define what each Python module must do before its pseudocode is replaced with working code. Tests protect the analytical definitions as well as the software: a function is not complete merely because it runs; it must preserve configured study periods, cross-year winters, classification audit fields, valid denominators, and data-quality warnings.

The framework uses `pytest`. Test inputs are deliberately small pandas DataFrames so failures can be understood without downloading the full City dataset. External services, files, and pipeline collaborators should be replaced with temporary files, monkeypatches, or small stubs in unit tests.

## Current baseline

There is one corresponding test module for each non-`__init__` module under `src/dp_activity`. On September 23, 2026, `python -m pytest -q --basetemp=.pytest_cache/rezoning-full` with the configured Python 3.13.14 environment reports:

```text
430 passed, 3 xfailed
```

The project-default test requires `"csv" in config.raw_snapshot_formats`, allowing additional raw formats such as the committed Parquet option. The processed-output expectation remains CSV-only. There are no unexpected failures in this run.

Passing tests cover configuration behavior, CLI dispatch and downloads, log archiving, Socrata and file-format adapters, repositories, cleaning, profiling, classification, all three validators, the abstract analysis contract, and pipeline orchestration with injected collaborators. They do not establish that a complete production pipeline can run.

The 3 expected failures cover sensitivity analysis, Power BI export, and chart saving. An unfinished function that raises `NotImplementedError` is reported as `XFAIL` by the shared `implemented()` helper in `tests/conftest.py`. Once the placeholder is removed, the actual assertions run and the test must either pass or fail normally. Both chart construction and saving remain unfinished; XFAIL counts are not counts of every unfinished function.

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

The next unfinished test target is `tests/analysis/test_sensitivity_analysis.py`.
Complete the remaining analyses, exporter, and chart tests, then
the frozen-fixture end-to-end smoke test. The 3 XFAILs identify scaffold tests,
not an exhaustive count of remaining integration tasks.

Geography tests cover community and ward counts, zero and small baselines, missing geography denominators, contextual periods, empty inputs, invalid schemas/configuration, and input preservation. CLI tests verify configured study labels and cleaner field names. An isolated temporary directory avoids a permissions error in the shared pytest temporary-folder cleanup.

## Installation and commands

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

A final smoke test should run the pipeline from a named frozen snapshot and configuration version through generated outputs in every configured format. It must verify that expected files exist, contain required columns, respect overwrite settings, preserve or archive the active pipeline log as configured, and agree with manifest counts.

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
