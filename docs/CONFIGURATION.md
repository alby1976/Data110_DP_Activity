# Configuration and Classification Rules

This project separates adjustable analysis choices from Python code. Project-wide settings belong in `config/settings.yaml`; record-classification logic belongs in `config/classification_rules.csv`. Keeping these choices in version-controlled files makes the analysis easier to review, reproduce, and audit.

Both files are present in the repository. The classification file includes validated-sample, provisional, fallback, and review statuses. Those labels support review but do not replace a documented classification audit.

## `config/settings.yaml`

This YAML file is the central source for project metadata, data access, analysis boundaries, quality checks, seasons, and output locations.

Chart creation is currently a Python API rather than a CLI output stage.
`ChartFactory(style={...})` accepts local Matplotlib rcParams overrides.
`monthly_volume(table, policy_boundaries={label: date(...)})` consumes the
`monthly_volume` result columns Period, YearMonth, PermitCount, and optional
IsPartialMonth. Call `save(figure, path)` explicitly for PNG, SVG, or PDF at
150 DPI with tight bounds; existing chart files are replaced. The factory uses
a headless canvas and does not change global plotting settings. Matplotlib
3.10.8 is pinned as a runtime dependency.

`ChartFactory.monthly_heatmap(table)` uses the same monthly analysis columns.
It creates one month-by-year panel per policy period with a shared count scale.
Gray cells and dashes mean no supplied data, not zero permits. Asterisks mark
partial months; question marks indicate unknown coverage. Saving is explicit:

```python
from pathlib import Path
from dp_activity.visualization.chart_factory import ChartFactory

charts = ChartFactory()
figure = charts.monthly_heatmap(analysis_tables["monthly_volume"])
charts.save(figure, Path("reports/monthly_heatmap.png"))
```

SVG and PDF destinations are also supported. Heatmaps are available through
the Python API; the CLI does not yet automatically create chart outputs.

Two seasonal APIs consume `analysis_tables["seasonal_summary"]`:

```python
season_year = charts.seasonal_year_heatmap(analysis_tables["seasonal_summary"])
season_year_rate = charts.seasonal_year_heatmap(
    analysis_tables["seasonal_summary"], metric="DP_Rate30"
)
season_period = charts.seasonal_period_heatmap(analysis_tables["seasonal_summary"])
```

In Jupyter, use `display(figure)` for any returned figure. Seasonal rows are
Winter, Spring, Summer, Fall. Year charts keep policy-period panels separate;
Winter December 2023–February 2024 appears under 2024. These APIs require the
standard meteorological season labels and starts. Complete seasons are included
by default. `include_partial=True` includes known partial seasons and marks cells
with `*`; unknown completeness is always excluded. Policy-period cells pool
counts and exposure days before multiplying by 30. Unknown or nonpositive
contributing exposure leaves a rate cell missing. Existing `DP_Rate30` values
are not averaged or trusted as inputs. Missing/excluded cells remain gray.

| Section | Purpose | Important settings |
|---|---|---|
| `project` | Identifies the project and author | project name, course, author |
| `data_source` | Defines where data comes from | provider, dataset ID `6933-unw5`, API URL, source type, optional app-token environment variable |
| `paths` | Defines repository-relative locations | raw, interim, processed, reports, classification rules |
| `storage` | Selects persisted data names, overwrite behavior, timestamp naming, and formats | output basename, residential-only cleaned export, overwrite and timestamp controls; raw: `csv`, `json`, `jgeojson`, `parquet`; processed: `csv`, `json`, `parquet`, `xlsx`; Excel layout |
| `study_periods` | Defines inclusive policy windows | Before, During, Early Post-Repeal |
| `analysis` | Controls analytical definitions | primary date, processing fields, small-base threshold, classification defaults |
| `seasons` | Maps calendar months to seasons | Fall, Winter, Spring, Summer |
| `quality_checks` | Defines required checks | unique permit number, required columns, warning conditions |
| `outputs` | Names generated tables | clean permits, summaries, audit table |
| `logging` | Controls pipeline records | level, active log file, archive toggle, archive directory, timestamp format |

### Current configured values

The committed `settings.yaml` currently describes the **Calgary Development Permit Activity** project for DATA 110. It reads from the City of Calgary Open Data Socrata dataset `6933-unw5` at `https://data.calgary.ca/resource` using JSON results. An optional token is read from the `SOCRATA_APP_TOKEN` entry in the local file configured by `paths.env_file`, not from a token value in the committed YAML file or a process-environment lookup.

Configured repository paths are:

| Setting | Current value | Purpose |
|---|---|---|
| `paths.env_file` | `config/dp.env` | local, ignored environment-variable file |
| `paths.raw_data` | `data/raw` | immutable source snapshots |
| `paths.interim_data` | `data/interim` | intermediate working data |
| `paths.processed_data` | `data/processed` | cleaned and transformed analysis outputs |
| `paths.classification_rules` | `config/classification_rules.csv` | ordered classification-rule table |
| `paths.reports` | `reports` | report and pipeline outputs |
| `paths.figures` | `reports/figures` | generated figures |
| `paths.tables` | `reports/tables` | generated summary tables |

Configured study periods are:

| Period key | Label | Start | End |
|---|---|---|---|
| `before` | Before | `2022-08-06` | `2024-08-05` |
| `during` | During | `2024-08-06` | `2026-08-03` |
| `post_repeal` | Early Post-Repeal | `2026-08-04` | open-ended |

The `config/dp.env` file is intentionally ignored by Git. It may define `SOCRATA_APP_TOKEN`,
but the token value must not be copied into `settings.yaml`.
The configuration loader reads simple `NAME=value` lines, ignores blank lines and
comments, supports `export NAME=value`, and exposes the token through the
configured `data_source.app_token_env` name. Missing `config/dp.env` files are treated as
empty local settings so a fresh clone remains usable without credentials.

The committed storage settings use `development_permits_residential` as the shared output stem,
allow generated outputs to overwrite previous generated files, and request CSV and
Parquet raw snapshots plus a combined Excel workbook for processed outputs.
`storage.processed_output_formats` is `[xlsx]` and `storage.excel_layout` is
`one_workbook`; processed CSV is commented out. Processed table export supports
CSV, JSON, Parquet, and Excel.

The [Conda setup](../README.md#conda) installs the project with `dev`, `parquet`,
and `excel` extras from `pyproject.toml`, as does `requirements-dev.txt` in a
standard virtual environment. No additional writer installation is needed with
either full setup. For a minimal installation, activate its environment and run
`python -m pip install -e ".[parquet,excel]"` from the repository root.

Timestamped output names are disabled by default. When `storage.include_timestamp` is
`true`, the writer appends the current UTC date/time using
`storage.timestamp_format` before the file extension. When the caller supplies an
output label and data-period label, timestamped names use this order:
`<base>_<label>_<data-period>_<timestamp>.<extension>`.

The configured output labels are `permits_clean`, `monthly_summary`,
`seasonal_summary`, `community_summary`, `type_summary`,
`processing_summary`, and `bias_audit`. These are extension-free labels used by the implemented exporter; files are
created when the CLI pipeline or an enabled notebook export runs.

### Downloading configured raw snapshots

Run `dp-activity --settings config/settings.yaml download` from the repository
root. The command builds the Socrata endpoint from `data_source.api_base_url`,
`dataset_id`, and `format`, and uses `data_source.page_size` (default 50000) for
pagination. The source type must be `socrata` and the API format must be `json`;
snapshot storage formats are selected separately.

The optional token comes from the variable named by `data_source.app_token_env`
in the file configured by `paths.env_file`. Token values are excluded from
download metadata and command summaries.

The download includes the configured `study_periods`, filtered using the source
column corresponding to `analysis.primary_date_field`. Inclusive end dates
include the entire final day. The `post_repeal` period is omitted when
`analysis.include_early_post_repeal` is false.

One download is saved under `paths.raw_data` in every format listed in
`storage.raw_snapshot_formats`, using `storage.output_base_name`. Each snapshot
has a metadata sidecar with source, query, retrieval time, row count, and checksum.
Raw snapshots always use the repository's timestamped, collision-safe naming;
`overwrite_outputs`, `include_timestamp`, and `timestamp_format` govern generated
analysis outputs rather than immutable raw snapshots.

### Interpretation rules

- All paths are resolved from the repository root, not from the user's current directory.
- Configuration dates use ISO format (`YYYY-MM-DD`) and study-period endpoints are inclusive.
- The `before` and `during` periods must not overlap.
- Every month number from 1 through 12 must appear in exactly one season.
- `storage.output_base_name` is an extension-free file stem; `storage.raw_snapshot_formats` and `storage.processed_output_formats` supply supported format extensions such as `.csv`, `.json`, `.jgeojson`, and `.parquet`. Parquet requires the optional Parquet dependency group.
- `storage.overwrite_outputs` defaults to `true` in the project settings. Set it to `false` when an existing generated output should be preserved instead of replaced.
- `storage.include_timestamp` controls whether generated filenames include the current UTC date/time. `storage.timestamp_format` must be a nonblank `strftime` pattern that does not produce path separators. Optional label and data-period filename parts are normalized into filename-safe tokens.
- `logging.log_file` remains the current run log. When `logging.archive_existing` is `true`, an existing log should be moved to `logging.archive_dir` using `logging.archive_timestamp_format` before a new run starts.
- January and February belong to a winter that starts in December of the previous year.
- `analysis.primary_date_field` determines policy-period and seasonal assignment.
- `analysis.classification.unmatched_action: "Review"` labels unmatched records for review. The classifier retains them with residential inclusion and rezoning relevance set to false, together with audit fields.
- `analysis.community_analysis.minimum_baseline_count` is a nonnegative integer warning threshold (default 5). Geography analysis flags community and ward baselines strictly below it; equality is not flagged, and zero disables the warning. It does not remove records or suppress percentage changes for positive baselines.
- Output names identify generated files. They should not be edited manually because they must be reproducible from the snapshot, configuration, and code.

### Storage and logging settings

`storage.residential_only: true` restricts the cleaned permit export to rows with
`IncludeResidential=true`. It applies to every processed format, including the
cleaned-permit sheet in a combined Excel workbook. It does not filter downloads,
raw snapshots, validation reports, or the full-input reconciliation and bias audit.
The CLI still passes all classified records to its analysis strategies, which
select residential rows for residential measures. If this setting is omitted or
false, the CLI exports all cleaned rows. Direct `PowerBIExporter` callers default
to false; both exploration notebooks explicitly enable residential-only exports.

The notebooks separately retain all-permit source exploration and create
`residential_permits` for residential profiles, analyses, and charts. Their
analysis-table denominators therefore refer to residential input rows. Use each
notebook's `population_counts` or full-source export reconciliation for original
and excluded counts. Changing the export setting does not change membership;
edit the classification rules to change which applications qualify.

The CLI supplies configured study windows, season labels and ordered month lists,
and `analysis.primary_date_field` to `SeasonalAnalysis`. Direct callers may supply
an explicit `observation_end`; open-ended windows require it. The CLI reads
`retrieved_at_utc` from `<snapshot extension>.metadata.json` beside the snapshot
and converts its timezone-aware timestamp to a UTC calendar date. For example,
`frozen.csv` uses `frozen.csv.metadata.json`. The `run` option
`--observation-end YYYY-MM-DD` overrides metadata, including missing or invalid
sidecars. Without either source, command assembly fails with an actionable error.
The cutoff is inclusive and shared by season/processing features and
volume/seasonal analyses. Configured windows beginning after the cutoff are
still rejected by analyses; select study windows appropriate to snapshot coverage.
This does not verify publication completeness or sidecar checksums.
Without configured windows, the strategy
summarizes observed seasons only and cannot establish zero-activity exposure.
`outputs.seasonal_summary` names the full season table. Other returned tables use
their logical names as filename labels unless overridden in `outputs`.

The CLI supplies configured period order to `ProcessingAnalysis`; configured empty
periods remain visible. The feature builder applies
`analysis.processing_time.minimum_days` and supplies eligibility flags, which the
analysis consumes without applying a separate threshold. `ResidentialType`, when
present, enables a type summary. Direct callers may pass `community_column` to
request a community breakdown; the CLI leaves that optional breakdown disabled.
The committed `outputs.processing_summary` names the period summary. Processing
denominator and subgroup tables are exported using their logical names by default.

The CLI passes configured study-period labels in order to `GeographyAnalysis`.
The second period is compared with the first; later periods are contextual and
have null comparison fields. The CLI also supplies the cleaned `community` and
`ward` source names. Direct callers default to `Community`, `Ward`, and the
`Before`/`During` comparison, or can supply explicit constructor arguments.
Missing or unconfigured period labels must be resolved before aggregation.

The strategy returns `community_summary`, `ward_summary`, and
`geography_period_totals` in memory. Only `community_summary` currently has an
entry in the committed `outputs` settings; other returned tables use their logical
names as filename labels unless an exact-key override is supplied.

The `storage` section separates the output file stem from file formats. With the
current `output_base_name: "development_permits_residential"`, `xlsx`, and
`one_workbook` settings, the CLI produces
`data/processed/development_permits_residential_workbook.xlsx`.
If CSV is enabled, the cleaned table instead has the per-table filename
`development_permits_residential_permits_clean.csv` (alongside the workbook
if both formats are selected). Paths and extensions are configured separately;
the basename must not contain a directory or extension.

Changing the prefix affects newly downloaded raw snapshots as well as CLI
processed exports. Raw snapshots still contain all downloaded applications:
`residential_only` filters the cleaned permit export, not the raw download.
Existing frozen snapshot filenames remain valid and are not renamed.
The notebooks explicitly use `before_exploration` and
`complete_period_exploration` as their export basenames, independently of this
setting. See the [Power BI export guide](POWER_BI_PLAN.md#create-the-power-bi-input-files)
for the commands and notebook output locations.

The `outputs` mapping supplies extension-free labels for each generated table.
Its naming convention is
`<base>_<label>[_<study_period_label>][_<period>][_<timestamp>][_<current_date_time>].<format>`, where the base is
`storage.output_base_name` and each format comes from
`storage.processed_output_formats`. The optional study-period label comes from
`study_periods.*.label`, normalized into a filename-safe token. The separate optional
period identifies the analysis period, such as `2024-08`. Each optional component
is preceded by a single underscore. A UTC timestamp is included only when `storage.include_timestamp`
is true, formatted with `storage.timestamp_format`. For example,
`monthly_summary: "monthly_summary"` with the current base and CSV format names
the output `development_permits_residential_monthly_summary.csv`.
With the study-period label `During` and period `2024-08`, it becomes
`development_permits_residential_monthly_summary_During_2024-08.csv`.
The additional optional `current_date_time` component records the UTC file-generation
date/time after the optional timestamp. Its separate configuration and exporter
support remain to be implemented.

The implemented exporter uses `<base>_<label>[_<timestamp>].<format>` and writes
whole tables, not separate period files. The study-period, period, and additional
current-date/time suffixes described above remain planned. Exact logical-key
labels from `outputs` override defaults; absent labels fall back to table names.
For example, `monthly_volume` is exported under that name; `monthly_summary`
does not implicitly rename it. Labels use letters, digits, underscores or hyphens.
Supported processed formats are CSV, JSON, Parquet (`parquet` or `pq`), and Excel (`xlsx`).
Dates/datetimes are ISO text in every format, Boolean values remain Boolean, and
missing cells remain missing. Parquet requires an installed compatible engine.
One UTC timestamp is shared across the export. Returned path keys are logical
names for one format, or `name.format` for multiple formats. Case-insensitive
filename collisions are rejected before writing. Writes are atomic per file;
the exporter is not transactional across files. Overwrite-disabled repositories
choose numbered sibling filenames and return those actual paths.

The `overwrite_outputs` flag controls generated data products. When it is `true`, a
writer may replace an existing configured output. When it is `false`, writers should
preserve existing files and fail or choose a collision-safe alternative, depending on the
specific repository/exporter contract.

The `logging` section keeps `reports/pipeline.log` as the active run log. If
`archive_existing` is `true`, the CLI archives the previous log before a new `run`
command starts, using `archive_timestamp_format` to create names such as
`reports/logs/archive/pipeline_20260918_143022.log`.

Archiving an existing log is implemented. Creating a new run log and a complete
export manifest still requires implementation; configuring their paths alone does
not produce these artifacts.

The settings file uses standardized, code-facing `snake_case` names such as `permit_number` and `applied_date`. The current rule file identifies source fields using the City's lowercase API names, such as `proposedusedescription`. The ingestion/classification workflow must therefore use an explicit, tested name map and apply each rule either before renaming or after translating its `Field` value. Mixing the two naming systems without a map would silently break classifications.

### Implemented feature configuration

The CLI now binds `analysis.primary_date_field` and the configured study periods
to the period filter. It passes `seasons.*.label` and each ordered month list to
the season filter, and `analysis.processing_time.start_field`, `end_field`, and
`minimum_days` to the processing filter. `minimum_days` must be a nonnegative
integer; zero permits same-day decisions. Signed negative durations remain in
the data for audit and are invalid for processing summaries.

Both season and processing filters accept an explicit `observation_end` calendar
date. The CLI resolves it from the snapshot sidecar's UTC retrieval date, or from
`--observation-end YYYY-MM-DD` when supplied. It is not a YAML setting. Missing
or invalid metadata requires an explicit override; the CLI does not infer the
cutoff from the clock, file modification time, or latest application date.
Direct API callers that omit it may retain unknown open-window completeness and
follow-up. See [Methodology](METHODOLOGY.md) for feature semantics.

### Validation reports and preconditions

The CLI binds `quality_checks.required_columns` to `SchemaValidator`, the full
`quality_checks` mapping to `DataQualityValidator`, and loaded classification
rules to `ClassificationValidator`. These validators are implemented; they
return reports without modifying input data. The current pipeline collects
their findings and does not automatically stop on failed report statuses.

`require_unique_permit_number` defaults to true; false downgrades duplicates
from failures to warnings. The three `warn_on_*` options default to true; false
omits the corresponding check. Optional `minimum_row_count` fails below the
configured minimum. Optional `max_data_age_days` requires `reference_date` and
compares the latest valid application date with that explicit date. Both
thresholds must be nonnegative integers and are disabled when absent. Historical
snapshots should use a reference date appropriate to the selected study window.
See [Methodology](METHODOLOGY.md#4-data-quality-checks) for count semantics.

The Python workflow should stop with a clear message when:

1. the YAML cannot be parsed;
2. a required section or setting is missing;
3. a path attempts to leave the repository;
4. a date is invalid or primary periods overlap;
5. a month is duplicated or missing from the seasonal map;
6. the configured classification file is unavailable when classification is requested;
7. a storage format is unsupported, duplicated, or blank;
8. an output basename includes a path or extension;
9. a logging archive path attempts to leave the repository; or
10. a configured source or output field is not supported by the pipeline.

## `config/classification_rules.csv`

This CSV holds the ordered, data-driven rules used to classify records as residential or non-residential, assign a standardized residential type, and identify records that may be relevant to citywide rezoning. `RezoningRelevant` is an analytical flag, not an official City of Calgary designation.

### Residential population definition

An application belongs to this study's residential population when its first
matching enabled rule sets `IncludeResidential=true`. This is an analytical
definition, not a separate official City designation or a measure of new homes.
The executable definition is [classification_rules.csv](../config/classification_rules.csv);
comments under `analysis.classification` in [settings.yaml](../config/settings.yaml)
summarize it.

| Development or evidence | Current treatment |
|---|---|
| Rowhouse, townhouse, semi-detached dwelling, duplex, single-detached dwelling (including contextual), multi-residential development, backyard suite, secondary suite | Included by housing-form rules HF-001 through HF-017 using proposed-use or description evidence |
| Residential category fallbacks | HF-100 through HF-106 include identified residential categories, multi-family renovations, additions over 10 sq metres, and remaining `Residential -` categories when no earlier rule matches |
| Mixed-use or change-of-use application with qualifying housing evidence | Included when an earlier housing rule wins; the category alone does not establish inclusion |
| Accessory residential buildings | HF-018 includes these as `Accessory Residential Building`, with `RezoningRelevant=False`; inclusion does not imply a primary dwelling |
| Other accessory buildings, signs, home occupations, commercial/industrial uses, and mixed use or changes of use without qualifying housing evidence | Excluded when their exclusion rule wins; HF-019 excludes `ACCESSORY BUILDING` evidence |
| Relaxation applications not matched by an earlier rule | HF-906 includes these as `Residential Non-Housing`, with `RezoningRelevant=False`; inclusion does not imply new housing |
| Unclassified or unmatched application | Excluded from residential analysis and retained for review |

Rules run by ascending `Priority`, then `RuleID`; the first match wins. Specific
housing evidence currently precedes category exclusions. Matching is
case-insensitive under the committed settings. An included application remains
included even when flagged for classification review. `RezoningRelevant` is
separate and must not be used as a residential filter. Inclusion does not require
a valid decision date: processing-duration eligibility is a later restriction.
Counts cover all included applications, including qualifying renovations and
additions, rather than only new construction or completed dwellings.

### Rule-file columns

| Column | Type | Purpose |
|---|---|---|
| `RuleID` | text | Stable unique identifier written to audit fields, for example `HF-001` |
| `RuleGroup` | text | Groups rules by purpose; currently `HousingForm` |
| `Field` | text | City API field to test, such as `category` or `proposedusedescription` |
| `MatchType` | category | Operation: `exact`, `contains`, `starts_with`, or `regex` |
| `MatchValue` | text | Value or regular expression tested against the selected field |
| `IncludeResidential` | Boolean | Whether the record belongs in the residential analytical population |
| `ResidentialType` | text | Standardized housing or exclusion category |
| `RezoningRelevant` | Boolean | Analytical relevance flag |
| `Priority` | integer | Evaluation order; lower numbers run first |
| `Enabled` | Boolean | Allows a rule to be retained but disabled |
| `ValidationStatus` | category | Current evidence/review state: `validated_2026_sample`, `provisional`, `fallback`, or `review` |
| `Notes` | text | Reason for the rule and known limitations |

The allowed values and field names must be enforced in code. `ValidationStatus` is documentation, not proof: rules marked `validated_2026_sample` should still be traceable to a retained audit sample and method.

### Rule evaluation

1. Preserve all original source fields.
2. Apply only rules where `Enabled` is true.
3. Normalize surrounding whitespace and, because `case_sensitive` is false, compare text without case differences.
4. Evaluate rules in ascending `Priority`, using `RuleID` as a stable tie-breaker.
5. Use the first matching rule and record its `RuleID` in `ClassificationRule`.
6. Mark unmatched records according to `unmatched_action`, currently `Review`.
7. Set `ClassificationNeedsReview` for unmatched records and winning rules whose `ValidationStatus` is `review`, `provisional`, or `fallback`. Preserve the status so these review reasons can be reported separately. Report additional matches separately as potential conflicts; intentional fallback/catch-all overlaps do not automatically change the winning rule's review flag.
8. Log conflicting potential matches so priority does not conceal rule overlap.

The committed rules place specific housing-form evidence before category exclusions,
allowing qualifying housing in mixed-use applications. Changing that order changes
membership and requires review of affected records. A district name by itself does
not prove the proposed use or number of homes.

### Required rule-file checks

Before classification, the workflow should verify:

- required columns are present;
- `RuleID` values are unique and nonblank;
- priorities are valid integers;
- Boolean and categorical values use approved values;
- `Field` refers to an available City API field or a documented mapped equivalent;
- regex patterns compile successfully;
- enabled rules do not duplicate the same condition with different outcomes; and
- every applied rule can be traced to affected records.

## Audit and change control

### Excel processed-output option

The committed settings already enable `xlsx` with `one_workbook`. Conda setup and
`requirements-dev.txt` both include the Excel extra. For a minimal installation,
activate its environment and run `python -m pip install -e ".[excel]"`. To export
both CSV and Excel, enable `csv` alongside `xlsx`
under `storage.processed_output_formats` in `config/settings.yaml`:

```yaml
  processed_output_formats:
    - csv
    - xlsx
  excel_layout: one_workbook
```

Use only `xlsx` in that list for Excel-only output. Choose `storage.excel_layout`:

- `one_file_per_table` (API default; not the committed setting): one workbook per table, each with a `Data` sheet.
- `one_workbook`: one `<base>_workbook[_<timestamp>].xlsx` file containing one sheet
  per permit, analysis, validation, reconciliation, and bias-audit table.

Every worksheet contains an Excel table with the same name as its sheet.
This also applies to the `Data` sheet in one-file-per-table exports. Empty inputs
use one blank placeholder row for Excel compatibility; remove all-null rows in
Power Query before counting or analyzing records. Sheet names must also be valid
Excel table names; invalid names or blank/duplicate column headers fail export.

Combined sheets use configured output labels, shortened to Excel's 31-character
limit. Case-insensitive collisions and the reserved `History` name receive numeric
suffixes. The returned output-path key is `workbook.xlsx`. Other formats still
produce separate files per table. No implicit index column is written.
Naming and overwrite rules are the same as other formats. Dates retain
the exporter's ISO-text representation; text resembling formulas or URLs remains
literal. Excel worksheet size and cell-length limits apply; use CSV or Parquet
for tables that exceed Excel's limits. Excel is not a raw snapshot format.

The CLI and notebook optional export cells use this setting. Reload the notebook's
configuration cell after changing YAML; restart the kernel after updating the
installed code. Excel (`xlsx`) with `one_workbook` is the committed configuration.
Workbook writes are atomic:
a failed workbook write does not replace an existing destination.

### Complete-period notebook controls

Both exploration notebooks read `analysis.heatmaps.metrics`, defaulting to
`[PermitCount, DP_Rate30]`. The list must be nonempty and contain unique supported
measures. Month × Year and Season × Year display one heatmap per measure.
DP30 means `PermitCount / ExposureDays * 30`, calculated from residential counts
and exposed calendar days. Missing/nonpositive exposure remains unavailable;
partial coverage stays marked. Season × Policy Period always displays pooled
DP30. With both measures enabled, each notebook produces six figures in memory;
optional exports include `month_year_dp30.png` and `season_year_dp30.png`.

The [complete-period notebook](../notebooks/02_complete_period_exploration.ipynb)
reads study periods, classification rules, formats, and output labels from the
project configuration. Its interactive controls are cell variables, not additional
YAML settings:

| Variable | Default | Effect |
|---|---|---|
| `SNAPSHOT_FILENAME` | `development_permits_20260925_045241.parquet` | Pins the offline analysis snapshot |
| `REFRESH_DOWNLOAD` | `False` | Set true to download all configured periods into new immutable snapshots |
| `REVIEW_LIMIT` | `10` | Limits examples displayed, not the analyzed population or complete classification review register |
| `INCLUDE_PARTIAL_SEASONS` | `False` | Excludes partial seasons from seasonal charts |
| `analysis.heatmaps.metrics` | `[PermitCount, DP_Rate30]` | Both count and DP30 views in monthly/year and seasonal/year heatmaps |
| `EXPORT_EXPLORATORY_OUTPUTS` | `False` | Enables optional table and PNG exports |

After a refresh, copy the printed Parquet filename into the cell source and reset
`REFRESH_DOWNLOAD=False` to preserve repeatable offline runs. Settings and rules
remain live project files; their displayed hashes record which versions were used.

Each enabled export creates `reports/notebook_complete_period/<unique-run-id>/`
with `tables/` and `figures/` subdirectories. Tables use
`config.processed_output_formats` and configured `outputs` labels, with the
`complete_period_exploration` basename. The notebook explicitly disables table
overwrite and uses a new run directory, independently of the global
`storage.overwrite_outputs` setting. Charts are PNG files. The output-path table
lists generated artifacts. Writes are per file, so an unsuccessful export can
leave a partially populated run directory. The default disabled branch has been
verified; the enabled branch has not been run against this snapshot.

### Recording analysis inputs

Each processed permit should retain `ClassificationRule`, `ClassificationNeedsReview`, and the rule's `ValidationStatus` alongside its original category, use, description, and district fields. The pipeline should also report rule coverage, unmatched counts, review counts, provisional/fallback counts, and potential conflicts by study period.

Changes to either configuration file can change reported results. Each final analysis should therefore record:

- the Git commit used;
- the source-data retrieval timestamp and snapshot identifier;
- a copy or checksum of both configuration files;
- the number of records matched by each enabled rule; and
- sensitivity results for reasonable broader and narrower classifications.

No rule should be changed solely because it produces an inconvenient result. Changes should include a reason in the commit history and, where relevant, in the rule's `Notes` field.
