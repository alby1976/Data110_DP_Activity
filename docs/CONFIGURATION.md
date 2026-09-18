# Configuration and Classification Rules

This project separates adjustable analysis choices from Python code. Project-wide settings belong in `config/settings.yaml`; record-classification logic belongs in `config/classification_rules.csv`. Keeping these choices in version-controlled files makes the analysis easier to review, reproduce, and audit.

Both files are present in the repository. The classification file includes validated-sample, provisional, fallback, and review statuses. Those labels support review but do not replace a documented classification audit.

## `config/settings.yaml`

This YAML file is the central source for project metadata, data access, analysis boundaries, quality checks, seasons, and output locations.

| Section | Purpose | Important settings |
|---|---|---|
| `project` | Identifies the project and author | project name, course, author |
| `data_source` | Defines where data comes from | provider, dataset ID `6933-unw5`, API URL, source type |
| `paths` | Defines repository-relative locations | raw, interim, processed, reports, classification rules |
| `storage` | Selects persisted data names, overwrite behavior, and formats | output basename, overwrite flag, and raw snapshot/processed output formats: `csv`, `parquet`, or both |
| `study_periods` | Defines inclusive policy windows | Before, During, Early Post-Repeal |
| `analysis` | Controls analytical definitions | primary date, processing fields, small-base threshold, classification defaults |
| `seasons` | Maps calendar months to seasons | Fall, Winter, Spring, Summer |
| `quality_checks` | Defines required checks | unique permit number, required columns, warning conditions |
| `outputs` | Names generated tables | clean permits, summaries, audit table |
| `logging` | Controls pipeline records | level, active log file, archive toggle, archive directory, timestamp format |

### Interpretation rules

- All paths are resolved from the repository root, not from the user's current directory.
- Configuration dates use ISO format (`YYYY-MM-DD`) and study-period endpoints are inclusive.
- The `before` and `during` periods must not overlap.
- Every month number from 1 through 12 must appear in exactly one season.
- `storage.output_base_name` is an extension-free file stem; `storage.raw_snapshot_formats` and `storage.processed_output_formats` supply the `.csv` and/or `.parquet` extension. Parquet requires the optional Parquet dependency group.
- `storage.overwrite_outputs` defaults to `true` in the project settings. Set it to `false` when an existing generated output should be preserved instead of replaced.
- `logging.log_file` remains the current run log. When `logging.archive_existing` is `true`, an existing log should be moved to `logging.archive_dir` using `logging.archive_timestamp_format` before a new run starts.
- January and February belong to a winter that starts in December of the previous year.
- `analysis.primary_date_field` determines policy-period and seasonal assignment.
- `analysis.classification.unmatched_action: "Review"` prevents an unrecognized value from being silently included or excluded.
- `community_analysis.minimum_baseline_count` is a warning/filter threshold for unstable percentage changes, not a deletion rule for the source data.
- Output names identify generated files. They should not be edited manually because they must be reproducible from the snapshot, configuration, and code.

### Storage and logging settings

The `storage` section separates the output file stem from the file formats. For example,
`output_base_name: "development_permits"` with `processed_output_formats: ["csv",
"parquet"]` gives downstream writers enough information to produce
`development_permits.csv` and `development_permits.parquet` without duplicating file
names in code. The basename must not include a directory or extension because paths and
formats are configured separately.

The `overwrite_outputs` flag controls generated data products. When it is `true`, a
writer may replace an existing configured output. When it is `false`, writers should
preserve existing files and fail or choose a collision-safe alternative, depending on the
specific repository/exporter contract.

The `logging` section keeps `reports/pipeline.log` as the active run log. If
`archive_existing` is `true`, the CLI archives the previous log before a new `run`
command starts, using `archive_timestamp_format` to create names such as
`reports/logs/archive/pipeline_20260918_143022.log`.

The settings file uses standardized, code-facing `snake_case` names such as `permit_number` and `applied_date`. The current rule file identifies source fields using the City's lowercase API names, such as `proposedusedescription`. The ingestion/classification workflow must therefore use an explicit, tested name map and apply each rule either before renaming or after translating its `Field` value. Mixing the two naming systems without a map would silently break classifications.

### Validation before execution

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

### Current schema

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
7. Set `ClassificationNeedsReview` for unmatched records and rules whose `ValidationStatus` is `review`; report provisional and fallback classifications separately.
8. Log conflicting potential matches so priority does not conceal rule overlap.

Specific exclusions and exact matches should normally have higher priority than broad `contains` or `regex` rules. A district name by itself should not automatically prove the proposed use or number of homes.

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

Each processed permit should retain `ClassificationRule`, `ClassificationNeedsReview`, and the rule's `ValidationStatus` alongside its original category, use, description, and district fields. The pipeline should also report rule coverage, unmatched counts, review counts, provisional/fallback counts, and potential conflicts by study period.

Changes to either configuration file can change reported results. Each final analysis should therefore record:

- the Git commit used;
- the source-data retrieval timestamp and snapshot identifier;
- a copy or checksum of both configuration files;
- the number of records matched by each enabled rule; and
- sensitivity results for reasonable broader and narrower classifications.

No rule should be changed solely because it produces an inconvenient result. Changes should include a reason in the commit history and, where relevant, in the rule's `Notes` field.
