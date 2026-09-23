# Power BI Dashboard Plan

The dashboard should answer the research questions in three pages without turning the submission into a cockpit from a budget airline.

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

Final column names may change, but the measure logic should follow this pattern.

```DAX
Permit Count =
DISTINCTCOUNT(FactPermits[PermitNum])
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
    FactPermits[IncludeResidential] = TRUE(),
    FactPermits[RezoningRelevant] = TRUE()
)
```

```DAX
Median Processing Days =
CALCULATE(
    MEDIAN(FactPermits[ProcessingDays]),
    FactPermits[HasValidProcessingDays] = TRUE()
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

The implemented `rezoning_summary` uses all included residential records as its
denominator, including review records. Display ReviewCount and RelevantReviewCount
as overlapping audit counts, not additional relevance categories. Rule/type/district
audits use group-local denominators. Imported RezoningRelevantShare is fractional;
PercentChange and ShareChangePercentagePoints use percent/percentage-point units.
Do not multiply imported percent-unit values by 100 again. Empty denominators and
zero-baseline percent changes remain blank. Export is still pending. These Python
counts are record counts; verify identifier uniqueness when reconciling the
distinct-count DAX measures. Label relevance as project-defined, not an official
City designation or evidence of a causal policy effect.

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
