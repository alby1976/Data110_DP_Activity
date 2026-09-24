# Python Design Patterns

## Purpose

The project uses a small set of design patterns to keep data access, analytical rules, orchestration, and output formats separate. Each non-package source module records its pattern and rationale in its module docstring so the reason remains visible beside the implementation.

Patterns are used only where they solve a concrete problem. A pattern name does not make code better by itself; if an abstraction does not improve testing, replacement, auditability, or clarity, it should not be added.

This overview includes both implemented components and scaffolded contracts. Adapters,
repositories, configuration, cleaning, profiling, classification, CLI dispatch,
pipeline orchestration, all three validators, all three feature filters, and volume,
development-type, geography, processing-time, seasonal, and rezoning analyses are implemented. The injected sensitivity runner is implemented; Power BI table export is also implemented. Study-specific scenario wiring and chart operations remain
unfinished. The sequence below
describes the intended complete workflow; see [Testing Framework](TESTING.md) for
verified behavior and remaining expected failures. Profiling is available separately
and is not currently invoked by the CLI pipeline.

## Architecture overview

| Pattern | Source modules | Why it is used |
|---|---|---|
| Composition Root and Command | `cli.py` | Builds concrete dependencies in one place and dispatches the selected workflow |
| Adapter | `socrata_adapter.py`, `file_format_adapter.py`, `powerbi_exporter.py` | Keeps Socrata, storage-format, and Power BI details outside the analytical core |
| Repository | `raw_data_repository.py`, `output_repository.py` | Hides filesystem persistence behind project-owned operations |
| Facade and Dependency Injection | `analysis_pipeline.py` | Exposes one pipeline operation while accepting replaceable collaborators |
| Pipes and Filters | cleaner, profiler, feature modules, pipeline | Builds the workflow from explicit deterministic stages |
| Strategy | analysis and validation modules | Lets the pipeline execute different analyses or validations through consistent roles |
| Chain of Responsibility | `classifier.py` | Evaluates ordered rules until the first matching rule handles a permit |
| Specification and Value Object | `rule.py` | Represents each immutable classification predicate and outcome as auditable data |
| Factory | `rule_loader.py`, `chart_factory.py` | Centralizes construction of validated rules and consistently styled figures |
| Reflective Factory | `file_format_adapter.py` | Loads a custom output adapter from a configured Python class path while enforcing the adapter contract |
| Immutable Value Object and Factory Function | `config.py` | Loads YAML and local `config/dp.env` entries into frozen dataclasses; nested mutable values such as the raw settings dictionary still require caller discipline |
| Result Object/Table | validation and pipeline-result classes | Returns structured findings instead of relying on printed messages or hidden state |
| Functional Core | feature modules | Keeps date and feature rules deterministic, side-effect-free, and boundary-testable |

## How the patterns work together

1. `cli.py` acts as the composition root and creates the concrete adapter, repositories, pipeline stages, analyses, validators, and exporter.
2. The Socrata adapter wraps the third-party `sodapy.Socrata` client. It translates the client's `get()` operation into project-owned `iter_records()` and `download()` operations, adding bounded retries, page validation, repeated-page detection, and retrieval metadata. The raw-data repository stores an immutable snapshot.
3. The analysis-pipeline facade sends the snapshot through cleaning, classification, feature, validation, and analysis stages.
4. The classifier applies immutable rule specifications as an ordered chain of responsibility.
5. Strategy objects calculate independent analytical and validation outputs without adding large conditional blocks to the pipeline.
6. Repositories and the Power BI adapter persist project-owned results in external formats.
7. The configuration loader reads the local `config/dp.env` file into frozen value objects so credentials can be looked up by configured variable name without mutating process-wide environment state.

## Implementation rules

- Keep Socrata request logic inside the adapter.
- Add new snapshot formats by implementing `FileFormatAdapter`; do not add format branches to `SocrataAdapter`.
- Accept reflected file adapters only when they subclass `FileFormatAdapter` and implement `save()`.
- Keep file-format and filesystem details inside repositories or exporters.
- Construct concrete dependencies in the CLI composition root, not inside analytical classes.
- Inject collaborators into the pipeline so tests can use stubs and fakes.
- Keep feature functions free of network and filesystem side effects.
- Add an analysis by implementing the `Analysis` strategy contract instead of editing a central conditional statement.
- Keep classification rules in `config/classification_rules.csv`; the chain executes rules but does not invent them.
- Keep secret values in the ignored `config/dp.env` file; `config/settings.yaml` may name the file and variable but must not store the secret itself.
- Return structured validation results. The current pipeline collects reports and proceeds to analysis; a policy for stopping on fatal findings remains to be implemented.
- Do not create an interface with only one foreseeable implementation unless it creates a useful testing or dependency boundary.

## Pattern-focused testing

`SeasonalAnalysis` implements Strategy and composes existing season features,
VolumeAnalysis, and ProcessingAnalysis to keep calendar and duration rules
consistent. It generates configured exposure independently of observed records,
returns separate complete/partial/unknown tables, and performs no I/O. The CLI
injects season definitions and study windows. Tests exercise boundary splits,
cross-year winter, zero seasons, unknown exposure, and processing eligibility.

`ProcessingAnalysis` is an implemented Strategy consuming feature-stage validity
and censoring flags. It returns period and optional subgroup summaries plus a
denominator table without changing source records or performing I/O. The CLI
injects configured period order. Its statistics and feature-filter integration
are tested independently of the unfinished exporter.

`GeographyAnalysis` implements the shared `Analysis.run()` Strategy contract.
The CLI injects ordered study labels, the minimum-baseline threshold, and the
cleaner's `community` and `ward` field names. The strategy returns community,
ward, and denominator tables without changing input records or writing files.
Tests verify missing-location retention, primary-period comparisons, contextual
periods, and zero/small baselines independently of the unfinished exporter.

The period, season, and processing filters implement Functional Core / Pipes
and Filters: each returns a new table without filesystem, network, or clock
access. Configuration is injected by the CLI; optional observation horizons
must be supplied explicitly. Missing and invalid evidence stays visible through
nullable outputs and flags rather than being silently dropped. Tests exercise
these functions independently and check that input rows and indexes survive.

Validation uses injected `validate` callables with configuration or rules bound
by `functools.partial`. `SchemaValidator` and `DataQualityValidator` return lists
of frozen `SchemaIssue` and `QualityCheckResult` objects. `ClassificationValidator`
returns a DataFrame with a summary and optional human-label confusion rows.
These strategies preserve input records and leave stop-or-warn decisions to
the caller. Coverage and rule-status labels do not establish accuracy.

The tests should verify the reason for each pattern, not merely its class names:

- adapters are tested with external behavior replaced or monkeypatched;
- repositories are tested with temporary directories;
- injected pipeline collaborators are replaced with stubs;
- strategy implementations are tested through their common `run()` contract;
- chain order, first-match selection, unmatched records, and conflicts are tested explicitly;
- immutable value objects are checked for stable, validated data; and
- functional feature stages are tested with boundary dates and without I/O.

See [Testing Framework](TESTING.md) for the complete test workflow and completion gates.
