# Project Summary

## Development Permit Activity Before and During Calgary's Citywide Rezoning

### Background and purpose

Calgary implemented citywide rezoning on August 6, 2024 through Bylaw 21P2024. The change redesignated many low-density residential parcels and expanded where a broader range of housing forms could be considered. Repeal-related zoning changes took effect on August 4, 2026, with exemptions for some qualifying parcels and applications. Development-permit records provide a practical way to examine activity surrounding this policy period.

This project asks: **What differences in Calgary residential development-permit activity can be observed before and during citywide rezoning?** The wording is intentionally observational. A before/during comparison can identify changes and associations, but it cannot by itself establish that rezoning caused them.

### Data and study design

The project uses the City of Calgary's public **Development Permits** dataset (ID `6933-unw5`). It contains permit identifiers, application and decision dates, category and proposed-use information, land-use district, current status, community, ward, and geographic coordinates.

Permits will be classified by `AppliedDate` into two primary comparison periods:

- **Before rezoning:** August 6, 2022–August 5, 2024
- **During rezoning:** August 6, 2024–August 3, 2026

Data from August 4, 2026 onward may be shown as an incomplete early post-repeal indicator, but it will not be treated as a comparable third period.

### Analytics plan

Python will retrieve and profile the source data; standardize dates and text; remove or flag invalid records; classify residential and rezoning-relevant permits; calculate derived measures; create exploratory charts; and export validated tables for Power BI. Power BI will present an interactive dashboard with synchronized filters for period, community, ward, development type, permit status, and land-use district.

The Python design separates external systems from the analytical core through adapters and repositories, composes deterministic cleaning and feature stages as pipes and filters, applies ordered classification specifications as a chain of responsibility, and implements analyses as interchangeable strategies. The command-line module acts as the composition root, while the analysis pipeline provides a single facade over the workflow. These choices make the code easier to test and keep methodological rules auditable; they are documented in [Python Design Patterns](DESIGN_PATTERNS.md).

The Python workflow will use a behavior-first `pytest` framework with a matching test module for each source module. Small synthetic DataFrames will test period boundaries, cross-year seasons, classification priority and audit fields, missing and invalid values, denominator rules, processing-time validity, and export schemas. Integration and end-to-end tests will use a named frozen public-data fixture, and Python headline totals will be reconciled with Power BI before submission. Scaffold-related expected failures identify unfinished modules and will not be counted as passing checks.

The analysis will compare monthly and seasonal permit volume, development-type mix, community-level change, and processing time. Applied dates will be classified as Fall (September–November), Winter (December–February), Spring (March–May), or Summer (June–August). Winter will be treated as a cross-year season, such as Winter 2024–25. Both absolute and percentage change will be reported, because percentage change can exaggerate movement in communities with small baseline counts. Processing-time analysis will emphasize the median and interquartile range because long-running cases can distort the mean. Monthly, same-month, and complete-season comparisons will be used to expose seasonality without treating partial boundary seasons as complete.

### Expected contribution and related work

As of September 23, 2026, volume, development-type, geography, processing-time, seasonal, and rezoning analysis strategies are implemented. Geography outputs include community and ward counts,
Before/During changes, small-baseline warnings, and missing-geography totals.
The latest full suite reports **522 passed, no expected failures** for unfinished
stages. The sensitivity runner is implemented; study-specific scenarios still need CLI configuration. Table export is implemented. The chart API is implemented. The synthetic CLI table smoke test passes. CLI chart integration and Power BI
reconciliation remain pending; implemented summaries are not final study findings.

The City of Calgary already publishes planning-application statistics by community and ward, demonstrating the value of permit data for monitoring development activity. CMHC research also examines how land-use regulation and permitting relate to housing supply, affordability, and the pace of development. This project is narrower: it builds a reproducible, Calgary-specific before/during comparison of permit applications, documents its classification rules, and combines Python analysis with an interactive Power BI dashboard. It does not treat permit applications as completed housing units or attempt to reproduce CMHC's causal claims.

### Limitations

The analysis is observational and cannot isolate rezoning from interest rates, construction costs, population growth, housing demand, other policies, or administrative changes. Public text fields may not identify housing form perfectly, applications may cross policy boundaries, and current status can change over time. Bias will be reduced by freezing the final data snapshot, documenting inclusion and classification rules before calculating results, manually validating a reproducible sample, reporting missing and pending records, comparing like months and complete seasons, showing both counts and rates with their denominators, and running sensitivity checks with alternative reasonable definitions. These measures improve transparency and robustness but cannot remove confounding. Results will therefore be presented as measured differences in permit activity—not proof of policy impact.

### References

1. City of Calgary. [Development Permits open dataset](https://data.calgary.ca/Business-and-Economic-Activity/Development-Permits/6933-unw5).
2. City of Calgary. [Land Use Bylaw 1P2007 and Bylaw 21P2024](https://www.calgary.ca/planning/land-use/online-land-use-bylaw.html?sec=21P2024).
3. City of Calgary. [Repeal of Citywide Rezoning](https://www.calgary.ca/planning/projects/rezoning.html).
4. City of Calgary. [Planning applications by community or ward](https://www.calgary.ca/planning/application-statistics.html).
5. Canada Mortgage and Housing Corporation. [Land Use Regulations and the Impact on Housing in Canada](https://www.cmhc-schl.gc.ca/professionals/housing-markets-data-and-research/housing-research/research-reports/accelerate-supply/land-use-regulations-impact-housing-canada), 2026.
