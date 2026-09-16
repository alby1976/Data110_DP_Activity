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
    FactPermits[IsResidential] = TRUE()
)
```

```DAX
Rezoning-Relevant Permit Count =
CALCULATE(
    [Permit Count],
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

## Page 3 — Geography

### Purpose

Identify communities with the largest absolute and relative changes.

### Visuals

- map by community or permit location;
- ranked bar chart for absolute change;
- table with Before, During, absolute change, percentage change, and baseline warning;
- drill-through to a selected community's monthly trend.

Use both absolute and percentage change. Suppress or flag percentage rankings below a documented minimum baseline.

## Interaction requirements

- synchronize the primary slicers across pages;
- enable cross-highlighting where it helps interpretation;
- provide a reset-filters button;
- use report-page tooltips for definitions and sample size;
- add alt text to visuals;
- do not encode the same category with different colours on different pages;
- keep Before and During colours consistent throughout;
- label Early Post-Repeal as incomplete wherever it appears.

## Validation checklist

- [ ] Distinct permit totals match Python outputs
- [ ] Date table covers the full study window
- [ ] December, January, and February map to the same cross-year Winter label
- [ ] Season labels sort by `SeasonSortKey`, not alphabetically
- [ ] Partial boundary seasons are flagged or excluded from complete-season comparisons
- [ ] Period sort order is correct
- [ ] Percentage measures use `DIVIDE`
- [ ] Empty baselines do not produce infinite percentage change
- [ ] Median excludes invalid processing intervals
- [ ] Map coordinates are numeric and categorized correctly
- [ ] All page-level filters are documented
- [ ] Slicer synchronization behaves as intended
- [ ] Titles state whether a visual uses application or decision date
