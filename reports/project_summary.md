# Calgary Development Permit Analytics

Project Summary and Analytics Plan

Albert Leung · DATA 110

## Purpose and research question

This project examines how Calgary’s residential development permit application activity differed before and during the configured citywide rezoning study windows. It compares volume, residential composition, community patterns, seasonality, and recorded decision duration to provide a transparent description of planning activity.

## Data and study scope

The City of Calgary Development Permits dataset (6933-unw5) provides one application record per source row. Period assignment uses the application date: **Before**, August 6, 2022–August 5, 2024; **During**, August 6, 2024–August 3, 2026. **Early Post-Repeal**, August 4, 2026 onward, is contextual only. The pinned snapshot has an October 13, 2026 UTC retrieval horizon, 31,627 source records, four blank-address exclusions, and 18,015 classified residential applications.

## Preparation and quality controls

Preserve the frozen snapshot and metadata, verify its checksum and query coverage, standardize fields, and apply ordered residential classification rules. Add period, season, and processing-eligibility features; reconcile source, retained, and residential counts. Keep missing geography, review flags, partial windows, and invalid or unavailable decision durations visible. Review flags request investigation and do not automatically exclude applications.

## Analysis methods

- **Volume and seasonality:** Compare application counts, absolute and percentage changes, and applications per 30 exposed days (count ÷ exposure days × 30). Examine monthly trends and pooled complete-season rates; flag boundary fragments.
- **Residential types:** Compare counts and within-period shares by rule-based category. Read share changes alongside counts because a shrinking denominator can increase a category’s share.
- **Geography:** Compare community and ward counts, shares, and Before/During changes. Retain missing-location denominators and flag community or ward baselines below five applications.
- **Processing:** Compare median and quartile durations for eligible application-to-decision records, together with eligible and ineligible counts. Explain pending decisions and unequal follow-up.

## Reporting and validation plan

Deliver reproducible Python notebooks, traceable summary tables, and a Power BI report with Overview, Development Type & Processing, and Geography pages. Use `environment.yml` for Python 3.13 and Quarto CLI 1.9.38, and `pyproject.toml` for pinned analytics, test, Parquet, Excel, and notebook dependencies; install Power BI Desktop separately. Present the findings in a ten-minute talk with a two-minute live demonstration. Before accepting dashboard values, reconcile imported counts and processing statistics with Python outputs. Complete independent classification review and study-specific sensitivity checks using alternative inclusion rules and comparable seasonal coverage.

## Interpretation and limitations

The design supports descriptive associations, not a causal estimate of rezoning effects. Applications do not count dwelling units or completed homes. Economic conditions, reporting lag, source completeness, classification uncertainty, and incomplete decisions can influence observed differences. Exposure adjustment corrects calendar length only; the short recent period remains unsuitable for a full post-repeal comparison.

Project basis: [project overview](../docs/PROJECT_OVERVIEW.md), [presentation notebook](../notebooks/03_ten_minute_presentation.ipynb), and [project methodology](../docs/METHODOLOGY.md). Delivery guides: [Power BI plan](../docs/POWER_BI_PLAN.md) and [presentation plan](../docs/PRESENTATION_PLAN.md). Source: City of Calgary Development Permits, dataset 6933-unw5.
