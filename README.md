# Calgary Development Permit Activity

**DATA 110 Mini-Capstone Project**

This project examines how Calgary residential development-permit activity differed before and during the city's citywide rezoning period. It uses Python for data acquisition, cleaning, transformation, and exploratory analysis, then Power BI for interactive reporting.

The project studies **observable differences and associations**. It does not claim that rezoning caused every change in permit activity.

## Copyright and academic integrity

Copyright © 2026 Albert Leung. All rights reserved.

This repository contains an original academic project. It may be viewed for reference, but its original code, documentation, analysis, visualizations, Power BI materials, and presentation materials may not be copied, modified, or submitted for academic credit without prior written permission.

See the [copyright notice](LICENSE.md) and [academic integrity policy](ACADEMIC_INTEGRITY.md). City of Calgary source data is separately licensed under the Open Government Licence – City of Calgary and is not covered by this project's copyright restrictions.

## Research question

> What differences in Calgary residential development-permit activity can be observed before and during citywide rezoning?

The analysis focuses on six supporting questions:

1. Did monthly residential development-permit volume differ between the two periods?
2. Did the mix of residential development types change?
3. Which communities experienced the largest absolute and percentage changes?
4. Did typical processing time differ?
5. Did the share of rezoning-relevant residential permits change?
6. How did permit activity vary by season within each policy period?

## Study periods

The primary comparison uses two nearly equal periods and classifies permits by `AppliedDate`.

| Period | Start | End | Use in analysis |
|---|---:|---:|---|
| Before rezoning | 2022-08-06 | 2024-08-05 | Primary comparison |
| During rezoning | 2024-08-06 | 2026-08-03 | Primary comparison |
| Early post-repeal | 2026-08-04 | Latest available date | Context only; incomplete |

August 6, 2024 is the implementation date for Bylaw 21P2024. Calgary's repeal-related zoning changes took effect on August 4, 2026. The short post-repeal period is not treated as equivalent to the two primary periods.

## Data source

The primary source is the City of Calgary's [Development Permits](https://data.calgary.ca/Business-and-Economic-Activity/Development-Permits/6933-unw5) open dataset.

- Dataset ID: `6933-unw5`
- Publisher: The City of Calgary
- Unit of observation: one development-permit application
- Unique identifier: `PermitNum`
- Access: Socrata Open Data API and downloadable CSV
- API endpoint: `https://data.calgary.ca/resource/6933-unw5.json`

Important fields include application, decision and release dates; category and proposed use; land-use district; permit status and decision; community and ward; and latitude/longitude.

## Planned workflow

```mermaid
flowchart TD
    A["Calgary Open Data API"] --> B["Python: inspect and clean"]
    B --> C["Classify residential records"]
    C --> D["Create periods and metrics"]
    D --> E["Export analysis tables"]
    E --> F["Power BI dashboard"]
    D --> G["Python charts and checks"]
```

Python and Power BI serve different roles while using the same definitions:

- **Python:** retrieve, profile, clean, classify, validate, summarize, visualize, and export the data.
- **Power BI:** provide interactive comparisons by period, community, ward, permit type, status, and land-use district.

Socrata results can be saved as CSV, JSON, or GeoJSON by filename extension, or as Parquet when a compatible engine is installed. The committed settings request CSV and Parquet raw snapshots and CSV processed outputs. Processed table export supports CSV, JSON, and Parquet. The file writer uses interchangeable format adapters and can load a custom adapter through a validated Python class path; see [Python Design Patterns](docs/DESIGN_PATTERNS.md).

## Key measures

- residential applications per 30 exposed calendar days (`DP_Rate30 = PermitCount / ExposureDays × 30`), null when exposure is unknown;
- total and monthly residential permit counts;
- average and median monthly permit counts;
- absolute and percentage change between periods;
- development-type count and share;
- permit counts and processing measures by season;
- median processing days and interquartile range;
- rezoning-relevant permits as a share of residential permits;
- community-level change, with small-base warnings for percentage change.

Processing time is defined initially as:

```text
ProcessingDays = DecisionDate - AppliedDate
```

Only non-negative values with both dates present will be included in processing-time summaries. This rule will be checked against the actual data before results are reported.

### Seasonal classification

Each permit will also be classified from `AppliedDate` using meteorological seasons:

| Season | Months |
|---|---|
| Fall | September–November |
| Winter | December–February |
| Spring | March–May |
| Summer | June–August |

Winter crosses calendar years. For example, December 2024 through February 2025 will be labelled **Winter 2024–25**. A season start date and sort key will keep seasons in chronological order in Python and Power BI. Seasons cut by the study boundaries will be flagged as partial rather than compared as though they contained three complete months.

## Repository structure

```text
Data110_DP_Activity/
├── ACADEMIC_INTEGRITY.md
├── LICENSE.md
├── README.md
├── config/
│   ├── settings.yaml             # project-wide analysis settings
│   └── classification_rules.csv # ordered housing-form classification rules
├── docs/
│   ├── CONFIGURATION.md
│   ├── DATA_DICTIONARY.md
│   ├── DESIGN_PATTERNS.md
│   ├── BIAS_AND_MITIGATION.md
│   ├── DEVELOPMENT_PERMIT_BACKGROUND.md
│   ├── METHODOLOGY.md
│   ├── POWER_BI_PLAN.md
│   ├── PRESENTATION_PLAN.md
│   ├── PROJECT_SUMMARY.md
│   ├── REFERENCES.md
│   └── TESTING.md
├── data/
│   ├── raw/                 # downloaded source data; not committed
│   └── processed/           # cleaned Power BI inputs
├── notebooks/               # optional exploration notebooks
├── powerbi/                 # Power BI .pbix file
├── reports/                 # final summary and presentation exports
├── requirements-dev.txt     # pinned local testing dependencies
├── src/                     # reusable Python modules
└── tests/                   # pytest tree mirroring the Python modules
```

Folders and planned files shown above that are not yet present will be added as the analysis is implemented.

## Configuration

Analysis choices are kept outside the Python code where practical. [`config/settings.yaml`](config/settings.yaml) contains the data source, study periods, season definitions, quality checks, storage formats, output naming and overwrite behavior, and pipeline-log archive settings. [`config/classification_rules.csv`](config/classification_rules.csv) contains ordered, auditable rules for residential inclusion, housing type, and rezoning-relevance classification. Provisional, fallback, and review rules remain subject to the validation process; being committed does not magically make a rule correct.

See the [configuration and classification-rules guide](docs/CONFIGURATION.md) for the file schemas, validation requirements, rule precedence, and audit process.

The Python modules also identify their architectural or object-oriented pattern and explain why it is used. See the [Python Design Patterns](docs/DESIGN_PATTERNS.md) overview for how the adapters, repositories, pipeline, strategies, rule chain, factories, and functional feature stages fit together.

## Getting started

Use Python 3.10 or newer. From a fresh checkout, create a virtual environment:

```bash
git clone https://github.com/alby1976/Data110_DP_Activity.git
cd Data110_DP_Activity
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package, pinned development dependencies, and Parquet support (required by the committed raw-storage settings):

```bash
python -m pip install -r requirements-dev.txt
python -m dp_activity.cli --help
```

Download the configured study periods from the repository root:

```bash
python -m dp_activity.cli --settings config/settings.yaml download
```

The installed `dp-activity` command accepts the same arguments. Downloads require network access and write timestamped, immutable snapshots plus metadata sidecars to `data/raw`. The optional token is read from `config/dp.env`, using the name `SOCRATA_APP_TOKEN`; a missing file is allowed. See [Configuration](docs/CONFIGURATION.md) for filtering, credentials, and storage details.

The `run` command executes the table pipeline from a frozen raw snapshot:

```bash
python -m dp_activity.cli --settings config/settings.yaml run data/raw/SNAPSHOT.csv
```

It uses the snapshot sidecar's UTC retrieval date, or an explicit
`--observation-end YYYY-MM-DD` override. Offline smoke tests exercise the real
pipeline with synthetic records and CSV, JSON, and Parquet exports. This does not
establish final study validity: failed validation reports still allow export,
sensitivity scenarios remain unconfigured, and full provenance and automatic
charts remain pending. Profiling is available through `DataProfiler.profile()`;
there is no `profile` or `analyse` CLI command.

## Running the tests

The [exploratory notebook](notebooks/01_permit_exploration.ipynb) runs offline
against the pinned Before snapshot. All 16 code cells passed in a fresh kernel
on September 24, 2026, including validators, five residential analysis strategies,
a monthly line chart, and three heatmaps. Summaries reconcile to 7,940 residential
records. Seasonal charts use complete seasons by default; only Before coverage is
available. External notebook exports are disabled by default. Data-quality and
classification warnings remain for review. See the
[notebook explanation](notebooks/01_permit_exploration_explaination.md) for report
definitions and recorded findings. The separate synthetic CLI smoke test also
passes; neither establishes independent classification accuracy or policy impact.

Install the development dependencies and run the complete suite from the repository root:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests for unfinished pseudocode appear as `XFAIL`. This is expected while a function still
raises `NotImplementedError`. After you implement a function, its real assertions run:

- `.` means the behavior passed;
- `F` means the implementation returned a result but did not meet the expected behavior;
- `XFAIL` means that module still reaches a `NotImplementedError` placeholder.

This makes the test summary a progress checklist rather than treating unfinished modules as
completed work.

The September 24, 2026 baseline is **522 passed**. The configuration test requires CSV among the enabled raw snapshot formats and permits additional formats such as Parquet. See [Testing Framework](docs/TESTING.md#current-baseline) for details.

The full framework, test layers, implementation loop, fixture rules, and completion gates are
defined in the [Testing Framework](docs/TESTING.md).

## Documentation

- [Copyright notice](LICENSE.md)
- [Academic integrity policy](ACADEMIC_INTEGRITY.md)
- [Configuration and classification-rules guide](docs/CONFIGURATION.md)
- [Python design patterns](docs/DESIGN_PATTERNS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [One-page project summary](docs/PROJECT_SUMMARY.md)
- [Biases and mitigation plan](docs/BIAS_AND_MITIGATION.md)
- [Development permit background](docs/DEVELOPMENT_PERMIT_BACKGROUND.md)
- [Methodology and analysis rules](docs/METHODOLOGY.md)
- [Calculation assumptions and simplifications](docs/CALCULATION_ASSUMPTIONS.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)
- [Power BI dashboard plan](docs/POWER_BI_PLAN.md)
- [Presentation plan](docs/PRESENTATION_PLAN.md)
- [Testing framework](docs/TESTING.md)
- [References and related work](docs/REFERENCES.md)

## Limitations

- This is an observational before/during comparison, not a causal study.
- Interest rates, population, construction costs, housing demand, seasonality, and other policies changed during the study.
- Public permit descriptions may require transparent rule-based classification.
- An application can begin in one policy period and be decided in another.
- Current status fields can change after data is downloaded.
- Percentage changes can be misleading when a community has a small baseline count.
- The early post-repeal period is incomplete and is presented only as context.

The analysis will use a documented [bias and mitigation plan](docs/BIAS_AND_MITIGATION.md). Planned safeguards include freezing a reproducible data snapshot, validating classification rules against samples, separating applications from approvals and completed homes, reporting missingness and pending cases, comparing like months and complete seasons, showing denominators, and testing whether conclusions change under reasonable alternative definitions. These steps can reduce bias; they cannot turn an observational comparison into a causal experiment.

## Official references

- [City of Calgary Development Permits dataset](https://data.calgary.ca/Business-and-Economic-Activity/Development-Permits/6933-unw5)
- [Land Use Bylaw 1P2007 and Bylaw 21P2024](https://www.calgary.ca/planning/land-use/online-land-use-bylaw.html?sec=21P2024)
- [Citywide rezoning repeal and timeline](https://www.calgary.ca/planning/projects/rezoning.html)
- [Planning application statistics](https://www.calgary.ca/planning/application-statistics.html)
- [CMHC: Land Use Regulations and the Impact on Housing in Canada](https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-research/research-reports/accelerate-supply/land-use-regulations-impact-housing-canada)

## Project status

**Partial implementation.** Configuration, Socrata downloads, file-format adapters, raw/output repositories, cleaning, profiling, rule loading and classification, all three validators, period/season/processing feature filters, CLI dispatch, log archiving, and pipeline orchestration are implemented. Volume, development-type, geography, processing-time, seasonal, and rezoning analyses are implemented. The injected sensitivity runner is also implemented; study-specific scenarios remain unconfigured in the CLI. Power BI table export is implemented; chart creation and saving are implemented as an explicit Python API. Pipeline unit tests use injected collaborators; offline CLI smoke tests also exercise real collaborators with synthetic data. These do not establish final real-data findings. Classification review against source data, Power BI development, and result writing remain outstanding.

The frozen-fixture CLI smoke test passes. Study-specific
sensitivity scenarios, chart workflow integration, and full run provenance remain
unfinished. The validators return reports without
changing records; failed report statuses do not yet stop the pipeline. See the
[current implementation checkpoint](docs/IMPLEMENTATION_PLAN.md#current-implementation-checkpoint-september-23)
for the remaining sequence and integration work.

## Author

Albert Leung

DATA 110 Mini-Capstone
