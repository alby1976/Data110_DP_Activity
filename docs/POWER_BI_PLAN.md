# Power BI Dashboard Plan

The dashboard should answer the research questions in three pages without turning the submission into a cockpit from a budget airline.

## Create the Power BI input files

Use the complete-period notebook export to reproduce the notebook's current
Before/During comparisons. The Before notebook exports only its Before snapshot.
Raw download files are source snapshots; import the processed export for analysis.

### Export from the complete-period notebook

1. Install the project and Excel/Parquet dependencies in the project's activated
   Python environment if they are not already installed:

   ```powershell
   python -m pip install ".[excel,parquet]"
   ```

2. Check `config/settings.yaml`. The current configuration creates one Excel
   workbook containing all reporting tables:

   ```yaml
   storage:
     residential_only: true
     excel_layout: "one_workbook"
     processed_output_formats:
       - xlsx
   ```

   Edit the existing `storage` section rather than adding a duplicate section.
   To produce CSV files instead, select `csv` in `processed_output_formats`.
   Selecting both formats creates the workbook and separate CSV tables.

3. Open `notebooks/02_complete_period_exploration.ipynb`. Keep the pinned
   `SNAPSHOT_FILENAME` and `REFRESH_DOWNLOAD=False` to reproduce the current
   analysis offline. Run all cells from the top so current settings and
   classification rules determine the exported results.
4. In **Optional exploratory exports**, change
   `EXPORT_EXPLORATORY_OUTPUTS = False` to `True`, then execute that cell after
   the analysis and chart cells have completed.
5. Read the displayed output-path table. With the current settings, the workbook
   is created at:

   ```text
   reports/notebook_complete_period/<unique-run-id>/tables/complete_period_exploration_workbook.xlsx
   ```

   Each export uses a new run directory. The workbook contains 27 sheets:
   residential permit records, 21 analysis tables, three validation reports,
   reconciliation, and a bias audit. Six chart PNGs are also saved under the
   run's `figures/` directory with the default heatmap settings.
6. Return `EXPORT_EXPLORATORY_OUTPUTS` to `False` after exporting if ordinary
   notebook reruns should create no external files. Use the displayed path to
   identify the intended export; subsequent runs have different directories.

### Select and check the reporting tables

Import the generated Excel workbook into Power BI and select the sheets needed
for the report. With the current output labels, `permits_clean` is the
residential fact-table input. Supporting sheets include `permit_volume`,
`monthly_volume`, `type_summary`, `community_summary`, `processing_summary`,
`rezoning_summary`, `seasonal_summary`, `reconciliation`, and `bias_audit`.
Validation sheets use the `validation_` prefix; Excel labels longer than 31
characters are shortened. Importing the workbook does not create the planned
relationships or measures automatically.

Set date, numeric, and Boolean column types explicitly when preparing the model:
the exporter serializes date cells as ISO text. Keep permit identifiers as text.
Use the permit sheet for row-level analysis and summary sheets at their own
grain; do not combine detail and summary rows into one count. Do not sum repeated
period denominators across type or geography rows.

For the September 30 rule version, check the permit sheet's row count against
**17,870 residential applications**: 9,857 Before, 7,606 During, and 407 Early
Post-Repeal. Compare Power BI counts to the Python `reconciliation` sheet.
The cleaned permit sheet is filtered to residential applications; full-source
counts and exclusions are retained in reconciliation and validation exports.
HF-018 accessory residential buildings and HF-906 residential non-housing
applications are included, with rezoning relevance false.

The complete `classification_review_records` register remains in notebook
output and kernel memory; the optional exporter does not create a separate
review-register sheet. Review flags on residential permit rows and full-source
validation reports are exported. Investigate warnings before accepting results;
successful export does not certify classification accuracy or Power BI agreement.

### Alternative: export through the CLI

From the repository root with the project environment activated, run:

```powershell
python -m dp_activity.cli --settings config/settings.yaml run data/raw/development_permits_20260925_045241.parquet
```

Keep the snapshot's adjacent metadata sidecar so the CLI can use its UTC
retrieval date as the observation horizon. The configured processed directory
is `data/processed`. With the current `xlsx`/`one_workbook` settings and
`output_base_name: development_permits`, the table workbook is:

```text
data/processed/development_permits_workbook.xlsx
```

The CLI uses current rules and configured output labels. Its current
`overwrite_outputs: true` setting replaces existing generated files with the
same names; copy an earlier workbook elsewhere if it must be retained. The CLI
exports tables; chart generation is an explicit notebook/API workflow. CLI
analysis receives all classified records, while notebook analysis receives
residential-only records, so their `AllPermitCount` and `ExcludedCount` scopes
differ even when residential counts match. Keep one producing workflow per
comparison and use its reconciliation output.

### Before-only export

In `notebooks/01_permit_exploration.ipynb`, run all preceding cells, then enable
and execute its **Optional exploratory exports** cell. With the current settings,
the workbook is `reports/notebook_before/tables/before_exploration_workbook.xlsx`.
It contains only Before analysis. Table overwrite is disabled in this notebook;
if a previous file exists, preserve or relocate it before exporting again.
Figures use a separate unique directory under `reports/notebook_before/figures/`.

## Data model

Use a small star schema rather than one enormous table doing interpretive gymnastics.

| Table | Role | Key relationship |
|---|---|---|
| `FactPermits` | one row per permit | many-to-one to date, community, and type dimensions |
| `DimDate` | continuous calendar | `FactPermits[AppliedDate]` to `DimDate[Date]` |
| `DimCommunity` | community attributes | community code |
| `DimResidentialType` | standardized type | residential type key |
| `DimPeriod` | period label and sort order | period key |

Use an active relationship for `AppliedDate`. If decision-date analysis is needed, add an inactive relationship to the same date table and activate it in specific measures with `USERELATIONSHIP`.

`DimDate` should include `Season`, `SeasonStartDate`, `SeasonLabel`, `SeasonSortKey`, and `IsCompleteSeason`. Seasons are Fall (Sep–Nov), Winter (Dec–Feb), Spring (Mar–May), and Summer (Jun–Aug). Sort `SeasonLabel` by `SeasonSortKey`; otherwise Power BI will cheerfully arrange seasons alphabetically, which is correct only on a planet with unusual weather.

## Core measures

Use the implemented `IncludeResidential` field and the
[documented residential definition](CONFIGURATION.md#residential-population-definition).
The committed `storage.residential_only: true` setting means the cleaned
`FactPermits` input contains only included residential applications. Full-source
and excluded counts must come from the separate reconciliation export, not from
counting this filtered fact table. If cleaned exports are configured to include
all records, retain the inclusion filter in residential measures.

Notebook analysis tables receive residential-only input, so their
`AllPermitCount` and `ExcludedCount` differ in scope from CLI analysis tables,
which receive all classified records. Record the producing workflow when
importing tables and use full-source reconciliation for source totals.
Python counts application rows without deduplicating permit identifiers; use
`COUNTROWS` for matching counts and investigate duplicates separately.

The Python volume and seasonal tables now include `DP_Rate30`, residential
applications per 30 exposed days. Display this as a numeric rate, not a percentage.
Keep PermitCount and ExposureDays visible in tooltips. For disjoint time rows at a
consistent grain, recompute `30 * DIVIDE(SUM(PermitCount), SUM(ExposureDays))`
only when every contributing exposure is known and the sum is positive. Otherwise
return blank. Do not average rates, mix period totals with their monthly rows,
double-count seasonal partitions, or sum repeated exposure across geography/type
groups. Partial-period flags remain relevant even after normalization. Import
and file export are still pending.

The implemented seasonal tables distinguish true, false, and unknown completeness.
Use `complete_seasons` for complete-season comparisons, with partial and unknown
rows shown separately. Keep contextual policy periods separate even when a season
is complete. Preserve configured zero counts; do not convert null processing
statistics to zero. Supporting calendar-month means use complete months only.
Season completeness depends on the policy window and observation cutoff, so it
must remain at period × season grain; a single global date-dimension flag cannot
represent a summer split by a policy boundary. Export is still pending.

Final column names may change, but the measure logic should follow this pattern.

```DAX
Permit Count =
COUNTROWS(FactPermits)
```

```DAX
Residential Permit Count =
CALCULATE(
    [Permit Count],
    FactPermits[IncludeResidential] = TRUE()
)
```

```DAX
Rezoning-Relevant Permit Count =
CALCULATE(
    [Permit Count],
    FactPermits[RezoningRelevant] = TRUE(),
    FactPermits[IncludeResidential] = TRUE()
)
```

```DAX
Median Processing Days =
CALCULATE(
    MEDIAN(FactPermits[ProcessingDays]),
    FactPermits[HasValidProcessingDays] = TRUE(),
    FactPermits[IncludeResidential] = TRUE()
)
```

```DAX
Rezoning-Relevant Share =
DIVIDE(
    [Rezoning-Relevant Permit Count],
    [Residential Permit Count]
)
```

Before/during change measures should be tested carefully so slicers do not accidentally remove one of the comparison periods.

## Page 1 — Overview

### Purpose

Answer whether activity differed overall and show the timing of changes.

### Visuals

- cards: residential permits, monthly average, median processing days, rezoning-relevant share;
- monthly application line chart;
- seasonal comparison chart with partial seasons visibly flagged or filtered out;
- clustered column chart comparing Before and During;
- compact data-completeness indicator;
- annotation for August 6, 2024 and August 4, 2026.

### Slicers

- period;
- season and season label;
- ward;
- community;
- residential type;
- permitted/discretionary;
- current status.

## Page 2 — Development Type and Processing

### Purpose

Show whether the composition of residential applications and typical processing time differed.

### Visuals

- clustered bars: permit count by type and period;
- 100% stacked bars: type share by period;
- processing-time distribution or box-plot custom visual, if permitted by course rules;
- matrix: type, period, count, share, median processing days;
- tooltip with sample size and missing processing-date share.

Avoid comparing processing times without displaying the number of valid observations.

The implemented Python `processing_summary` supplies period-level median, mean,
quartiles, IQR, and valid/ineligible/pending/censored counts. Use
`processing_type_summary` for type-level statistics and `processing_period_totals`
for residential and nonresidential denominators once export is implemented.
Do not average subgroup medians or quartiles to obtain a period statistic.
`ValidShare` is fractional; audit counts may overlap and must not be added.
Preserve null statistics for empty valid cohorts. Pending/censored counts explain
eligibility and do not establish that two cohorts have comparable follow-up.

## Page 3 — Geography

### Purpose

Identify communities with the largest absolute and relative changes.

### Visuals

- map by community or permit location;
- ranked bar chart for absolute change;
- table with Before, During, absolute change, percentage change, and baseline warning;
- drill-through to a selected community's monthly trend.

Use both absolute and percentage change. Suppress or flag percentage rankings below a documented minimum baseline.

### Python geography table contract

The implemented strategy returns `community_summary` and `ward_summary` at
period × location grain, plus `geography_period_totals` at period grain. Export
and Power BI integration remain unfinished. Build the Before/During display by
pivoting `PermitCount` on `Period`; use the second configured period's
`AbsoluteChange` and `PercentChange`. Contextual periods have no change metrics.

`PermitShare` is fractional and can use percentage formatting directly.
`PercentChange` already uses percent units: divide by 100 before applying Power
BI percentage formatting, or display it as a number with a percent suffix.
Zero-baseline changes remain blank. Show `BaselinePermitCount` alongside
`SmallBaselineWarning`; the default threshold is fewer than 5 permits and applies
to both communities and wards. Any ranking filter must be disclosed.

Retain null locations as an explicit missing-geography row in tables and show
their counts beside maps. Do not geocode a missing group or confuse it with a
literal `Unknown` label. Use `geography_period_totals` for residential and missing
counts; repeated denominators in location summaries must not be summed.
Geography summaries count included records, without deduplication. Verify unique
permit identifiers before reconciling them with the distinct-count measures
above; investigate any differences instead of silently changing denominators.

## Interaction requirements

- synchronize the primary slicers across pages;
- enable cross-highlighting where it helps interpretation;
- provide a reset-filters button;
- use report-page tooltips for definitions and sample size;
- add alt text to visuals;
- do not encode the same category with different colours on different pages;
- keep Before and During colours consistent throughout;
- label Early Post-Repeal as incomplete wherever it appears.

## Bias-aware reporting

The dashboard should make important analytical risks visible instead of burying them in speaker notes:

- display the data retrieval date and maximum `AppliedDate`;
- show the valid denominator for processing-time measures;
- provide counts of pending, missing-date, unclassified, and excluded records;
- label application counts as applications, not housing units or completed homes;
- display baseline counts beside community percentage changes;
- flag or filter incomplete seasons;
- include a small-base warning for unstable community percentages;
- offer counts and shares together so changes in total volume are not mistaken for changes in composition;
- use a tooltip or information panel summarizing classification rules and residual limitations.

## Validation checklist

- [ ] Distinct permit totals match Python outputs
- [ ] Date table covers the full study window
- [ ] December, January, and February map to the same cross-year Winter label
- [ ] Season labels sort by `SeasonSortKey`, not alphabetically
- [ ] Partial boundary seasons are flagged or excluded from complete-season comparisons
- [ ] Period sort order is correct
- [ ] Percentage measures use `DIVIDE`
- [ ] Empty baselines do not produce infinite percentage change
- [ ] Community and ward counts, including missing groups, each reconcile to period residential totals
- [ ] Geography denominators are not summed across location rows
- [ ] Imported `PercentChange` values are not multiplied by 100 a second time
- [ ] Missing-location counts and any small-baseline ranking filters are visible
- [ ] Median excludes invalid processing intervals
- [ ] Map coordinates are numeric and categorized correctly
- [ ] All page-level filters are documented
- [ ] Slicer synchronization behaves as intended
- [ ] Titles state whether a visual uses application or decision date
- [ ] Pending and right-censored records are visible in processing-time views
- [ ] Every percentage displays or exposes its denominator
- [ ] Application counts are not labelled as homes constructed
- [ ] Bias and limitations information is accessible from every report page
