# Power BI Dashboard Plan

The dashboard should answer the research questions in three pages without turning the submission into a cockpit from a budget airline.

## Create the Power BI input files

### Prepare the Python environment

From the repository root, use the Conda environment defined in
[`environment.yml`](../environment.yml):

```bash
conda env create --file environment.yml
conda activate data110-dp-activity
python -m dp_activity.cli --help
```

If the environment already exists, activate it without repeating creation.
Conda supplies Python 3.13 and pip. The editable install reads runtime dependencies
and the `dev`, `parquet`, and `excel` extras from
[`pyproject.toml`](../pyproject.toml). Parquet support loads the frozen snapshot;
Excel support supplies XlsxWriter for workbook export. Both extras are included
in this setup and in `requirements-dev.txt`.

For a standard virtual environment, follow the
[README setup instructions](../README.md#getting-started), then run
`python -m pip install -r requirements-dev.txt` in that activated environment.
After changing Python dependencies, run
`python -m pip install -e ".[dev,parquet,excel]"` and `python -m pip check`
from the repository root in the selected environment.

For notebook exports, select the `data110-dp-activity` interpreter in PyCharm
and use it for notebook execution. The environment file does not install a
standalone Jupyter server or register a Jupyter kernel.

### Export the complete-period snapshot with the CLI

The committed `config/settings.yaml` selects `xlsx` processed output,
`excel_layout: one_workbook`, and `output_base_name: development_permits`.
Run the pipeline against the frozen snapshot:

```bash
python -m dp_activity.cli --settings config/settings.yaml run data/raw/development_permits_20260925_045241.parquet
```

Keep the adjacent `.metadata.json` sidecar with the snapshot; the CLI uses its
UTC retrieval date as the observation horizon. The combined workbook is written
to `data/processed/development_permits_workbook.xlsx`, with separate sheets for
cleaned permits, analysis, validation, reconciliation, and bias-audit tables.
The committed overwrite setting replaces an existing generated workbook.
Review validation reports before using exported results; validation failures
currently do not prevent export or CLI success.

To produce CSV inputs instead, set `storage.processed_output_formats` to `[csv]`.
For both formats, use `[csv, xlsx]`. CSV creates separate files for each table;
`storage.excel_layout` controls only Excel outputs. See the
[export configuration guide](CONFIGURATION.md#excel-processed-output-option)
for sheet naming, timestamp, and overwrite behavior.

### Export from an exploratory notebook

Open `notebooks/02_complete_period_exploration.ipynb`, keep
`REFRESH_DOWNLOAD=False` to reuse its pinned snapshot, and run cells in order.
Set `EXPORT_EXPLORATORY_OUTPUTS=True` in the optional export cell and run it
after the analysis cells. With the current Excel settings, its workbook is:

```text
reports/notebook_complete_period/<unique-run-id>/tables/complete_period_exploration_workbook.xlsx
```

Charts are saved under the same run's `figures/` directory. The Before-only
notebook exports only its Before snapshot; use the complete-period notebook
for Before/During comparisons. Consult the
[complete-period guide](../notebooks/02_complete_period_exploration_explanation.md)
and [Before guide](../notebooks/01_permit_exploration_explaination.md) for their
snapshot coverage and export options. A saved notebook with exports disabled
does not establish that an external workbook was generated.

### Import and reconcile in Power BI

Use **Get data > Excel workbook** for the combined workbook or **Text/CSV**
for separate CSV inputs. Select the cleaned-permit and summary tables needed
for the report, retaining validation, reconciliation, and bias-audit outputs
for review. Check date, numeric, and Boolean types in Power Query; exported
dates use ISO text and may need conversion.

Record whether each imported table came from the CLI or a notebook, together
with the snapshot filename, settings, and classification-rule version. Verify
residential totals, period counts, processing eligibility, and exposure values
against that same run before building report measures. Existing saved totals
may describe earlier rules. Generating a workbook does not verify Power BI
relationships, measures, or refresh results.

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
groups. Partial-period flags remain relevant even after normalization. File export is supported; Power BI reconciliation must be checked for each imported run.

The implemented seasonal tables distinguish true, false, and unknown completeness.
Use `complete_seasons` for complete-season comparisons, with partial and unknown
rows shown separately. Keep contextual policy periods separate even when a season
is complete. Preserve configured zero counts; do not convert null processing
statistics to zero. Supporting calendar-month means use complete months only.
Season completeness depends on the policy window and observation cutoff, so it
must remain at period × season grain; a single global date-dimension flag cannot
represent a summer split by a policy boundary. Export these tables using the workflow above.

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
for residential and nonresidential denominators in exported outputs.
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
is supported; Power BI relationships and measures still require reconciliation. Build the Before/During display by
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
permit identifiers separately; the COUNTROWS measures above match Python row counts.

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

- [ ] Application row counts match Python outputs; duplicate identifiers are audited separately
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
