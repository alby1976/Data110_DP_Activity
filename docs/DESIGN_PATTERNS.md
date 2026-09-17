# Python Design Patterns

## Purpose

The project uses a small set of design patterns to keep data access, analytical rules, orchestration, and output formats separate. Each non-package source module records its pattern and rationale in its module docstring so the reason remains visible beside the implementation.

Patterns are used only where they solve a concrete problem. A pattern name does not make code better by itself; if an abstraction does not improve testing, replacement, auditability, or clarity, it should not be added.

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
| Immutable Value Object | `config.py` | Prevents validated settings and period boundaries from changing during a run |
| Result Object/Table | validation and pipeline-result classes | Returns structured findings instead of relying on printed messages or hidden state |
| Functional Core | feature modules | Keeps date and feature rules deterministic, side-effect-free, and boundary-testable |

## How the patterns work together

1. `cli.py` acts as the composition root and creates the concrete adapter, repositories, pipeline stages, analyses, validators, and exporter.
2. The Socrata adapter retrieves external records, and the raw-data repository stores an immutable snapshot.
3. The analysis-pipeline facade sends the snapshot through cleaning, classification, feature, validation, and analysis stages.
4. The classifier applies immutable rule specifications as an ordered chain of responsibility.
5. Strategy objects calculate independent analytical and validation outputs without adding large conditional blocks to the pipeline.
6. Repositories and the Power BI adapter persist project-owned results in external formats.

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
- Return structured validation results and let the pipeline decide whether a finding is informational, a warning, or fatal.
- Do not create an interface with only one foreseeable implementation unless it creates a useful testing or dependency boundary.

## Pattern-focused testing

The tests should verify the reason for each pattern, not merely its class names:

- adapters are tested with external behavior replaced or monkeypatched;
- repositories are tested with temporary directories;
- injected pipeline collaborators are replaced with stubs;
- strategy implementations are tested through their common `run()` contract;
- chain order, first-match selection, unmatched records, and conflicts are tested explicitly;
- immutable value objects are checked for stable, validated data; and
- functional feature stages are tested with boundary dates and without I/O.

See [Testing Framework](TESTING.md) for the complete test workflow and completion gates.
