# Biases and Mitigation Plan

This project compares Calgary residential development-permit activity before and during citywide rezoning. It is an observational analysis of administrative data, so bias cannot be eliminated. The goal is to identify likely sources of distortion, reduce them where practical, test whether they change the findings, and disclose what remains.

## Bias register

| Potential bias | How it could distort the results | Steps to minimize it | Residual limitation |
|---|---|---|---|
| **Selection and coverage bias** | The dataset contains development-permit applications, not every construction activity, building permit, housing start, completed dwelling, or project that was considered but never submitted. | Define the population as published DP applications; avoid generalizing to all construction; compare selected aggregates with City application statistics where definitions align. | Unsubmitted projects and activities outside the DP system remain unobserved. |
| **Outcome substitution** | A permit application could be incorrectly presented as an approved permit, constructed project, or housing unit. One permit can also represent more than one unit. | Label each metric precisely; keep `AppliedDate`, `Decision`, `StatusCurrent`, and `ReleaseDate` distinct; do not estimate homes or units unless a validated unit field or external dataset supports it. | Permit activity is only one stage of the development pipeline. |
| **Classification bias** | Rule-based interpretation of category, proposed-use, description, or district text can misclassify residential type or rezoning relevance. | Use version-controlled `config/classification_rules.csv`; retain original fields and matched `RuleID`; assign `Review` to ambiguous values; manually inspect a seeded reproducible sample; report unmatched and conflicting matches; test broader and narrower definitions. | Free text and multi-use applications may remain ambiguous. `RezoningRelevant` is analytical, not an official City label. |
| **Confirmation and researcher bias** | Prior views about rezoning could influence category rules, chart selection, or interpretation. | Define questions and rules before viewing final comparisons; keep an analysis log; use code-generated tables; retain null and contradictory findings; ask another person to review a classification sample if feasible. | Judgment is still required when defining categories and explaining results. |
| **Temporal confounding** | Interest rates, population, housing demand, construction costs, labour supply, other policies, and administrative practices changed during the same period. | Use neutral before/during language; show monthly trends; discuss concurrent factors; consider contextual indicators if reliable; run sensitivity checks; avoid causal verbs. | A descriptive two-period design cannot isolate the independent effect of rezoning. |
| **Seasonality bias** | Construction and application activity varies through the year, so unequal month or season coverage could create a false difference. | Use equal primary windows; compare like calendar months; classify Fall, Winter, Spring, and Summer consistently; compare complete seasons; flag partial boundary seasons. | Weather and seasonal conditions differ from year to year even within the same named season. |
| **Policy-boundary misclassification** | Applications submitted near August 6, 2024 may have been planned under earlier expectations, while decisions can occur in another policy period. | Assign the primary period by `AppliedDate`; retain decision and release dates; identify cross-boundary cases; test reasonable transition-window exclusions around the implementation date. | No observed date reveals exactly when a developer made the underlying investment decision. |
| **Right-censoring and survivorship bias** | Recent or complex applications may still be pending. Calculating processing time only for completed cases can make recent performance look faster and omit long-running cases. | Report pending counts and follow-up time; restrict direct processing comparisons to cohorts with adequate observation time; use a fixed data cutoff; show completion proportions; perform sensitivity analysis excluding recent cohorts. | True processing time is unknown until unresolved cases finish; a full survival-analysis model may be beyond course scope. |
| **Mutable-record and refresh bias** | `StatusCurrent` and other fields can change after extraction, so rerunning the analysis later may produce different results. | Save a dated raw snapshot or reproducible extract; record retrieval time, query, row count, date range, and checksum; use the same frozen snapshot for Python, Power BI, and slides. | The frozen analysis will not contain later corrections or outcomes. |
| **Missing-data bias** | Missing dates, categories, community names, or coordinates may not be random and can disproportionately remove certain applications. | Profile missingness by period and subgroup; report exclusions and valid denominators; keep explicit missingness flags; avoid silently dropping records; compare included and excluded records on available fields. | The true values and reasons for missingness may be unavailable. |
| **Duplicate and unit-of-analysis bias** | Duplicate identifiers, multiple locations, amendments, or several permits for one development could inflate counts or overrepresent complex projects. | Test `PermitNum` uniqueness; investigate duplicates; preserve `LocationCount`; count distinct permits for headline measures; document whether related permits can be linked reliably. | Distinct permit applications are not necessarily distinct physical projects. |
| **Geographic bias** | Missing coordinates, multi-location permits, changing ward boundaries, and geocoding choices can misplace or exclude records. | Prefer stable community codes for comparison; validate coordinate ranges; flag multi-location permits; report unmapped counts; identify which ward-boundary vintage is used. | Community and ward results may not represent every location attached to a multi-location permit. |
| **Small-number and denominator bias** | A change from one to four permits appears as 300%, potentially dominating rankings despite a tiny baseline. | Show absolute and percentage change together; display the denominator; set and disclose a minimum-baseline warning or filter; avoid ranking unstable percentages as headline findings. | Any threshold is a reporting choice and should be tested for sensitivity. |
| **Aggregation bias and Simpson's paradox** | A citywide trend can differ from trends within communities or housing types because the composition of applications changes. | Report citywide and stratified results; compare counts and shares; inspect period-by-type and period-by-community tables; avoid treating an aggregate result as universal. | Fine stratification can create sparse groups and unstable estimates. |
| **Status/decision availability bias** | Approved, refused, cancelled, and pending applications have different data completeness and timelines. Filtering only approved records can make the application population look more successful or faster. | Begin with all in-scope applications; show outcome-specific subsets separately; disclose filters on every visual; report pending and unknown outcomes. | Current outcomes may change after the snapshot date. |
| **Data-publication bias or error** | The public administrative dataset may contain coding errors, delayed updates, or fields whose operational definition changed. | Review source metadata; test ranges and categories; reconcile major totals with City publications when definitions permit; record unexplained discrepancies rather than forcing agreement. | Internal City records and data-generation procedures may not be available for audit. |

## Required validation work

### Implemented seasonal safeguards

`SeasonalAnalysis` separates complete, partial, and unknown seasonal exposure,
retains configured zero-activity seasons, and reports like-month complete-exposure
means separately from partial and unknown months. Policy-boundary fragments are
not merged into a complete season. These controls do not remove temporal
confounding or make contextual periods equivalent. Snapshot cutoff wiring,
sensitivity comparisons, source review, and final dashboard reconciliation remain
required before accepting final findings.

### Implemented processing safeguards

`ProcessingAnalysis` reports pending and right-censored residential counts beside
valid-duration statistics and retains counts for ineligible intervals. Optional
feature flags distinguish date errors, missing dates, negative durations, and
records beyond an explicit observation horizon. Unknown audit counts remain null,
and overlapping reasons are not a partition of the excluded population.
The summaries do not correct for right-censoring or establish adequate follow-up.
CLI observation-horizon wiring, minimum-follow-up eligibility, and cohort
sensitivity analysis remain outstanding.

### Implemented geography safeguards

`GeographyAnalysis` retains missing community and ward groups in residential
denominators, reports their counts separately, and flags primary-period baselines
below the configured threshold (default 5). Zero-baseline percentage changes
are null; positive small baselines remain visible with warnings. Later periods
are contextual and receive no automatic change calculation.

These safeguards are unit-tested, but do not establish geographic accuracy.
The current strategy groups trimmed source labels, not stable community codes,
and does not reconcile historical ward boundaries, allocate multi-location
permits, or deduplicate records. Source review, mapping checks, baseline-threshold
sensitivity analysis, and dashboard reconciliation remain required. Missing
community and ward counts can overlap and must not be added as a unique total.

### 1. Classification audit

Create a reproducible validation sample using a fixed random seed. Include:

- records from both primary periods;
- every major residential classification;
- records marked `Review`;
- a sample classified as non-residential;
- records with multiple proposed uses or districts.

Manually compare the derived classification with the original text fields. Report sample size, disagreement count, corrected rules, and remaining ambiguous cases. If a second reviewer is available, compare decisions on the same sample.

The file schema, priority rules, validation checks, and audit fields are defined in [Configuration and Classification Rules](CONFIGURATION.md). The final report should identify the Git commit and configuration versions used so later rule changes cannot silently alter the reported findings.

### 2. Missingness and exclusion table

For each period, report:

- source records;
- records excluded from the study window;
- residential, non-residential, and unclassified records;
- missing application or decision dates;
- invalid processing intervals;
- pending cases;
- records missing community or usable geography.

### 3. Sensitivity analyses

At minimum, recalculate headline findings under:

1. a narrow and a broad residential classification;
2. a narrow and a broad rezoning-relevant classification;
3. the primary application-date rule and a version excluding a transition window near August 6, 2024;
4. all eligible seasons and complete seasons only;
5. all communities and communities above the disclosed baseline threshold;
6. processing cohorts with different minimum follow-up periods.

If a conclusion changes materially, present that instability as a finding rather than selecting the preferred result.

## Reporting rules

- State the population, date window, retrieval date, filter, and denominator.
- Distinguish permit applications from permits approved, dwellings authorized, construction starts, and completed homes.
- Use **before/during difference** or **association**, not **effect** or **caused**.
- Display uncertainty caused by missing, pending, ambiguous, or small samples.
- Show counts beside percentages and shares.
- Report the number of valid observations beside processing-time statistics.
- Keep incomplete post-repeal data separate from the equal primary periods.
- Retain and report evidence that contradicts the main narrative.

## Bias review checklist

- [ ] Analysis population is defined as development-permit applications
- [ ] Final raw-data snapshot and retrieval metadata are frozen
- [ ] Inclusion and classification rules are version controlled
- [ ] Classification sample has been manually audited
- [ ] Missingness and exclusions are reported by period
- [ ] Pending cases and right-censoring are addressed
- [ ] Like-month and complete-season comparisons are included
- [ ] Transition-window sensitivity check is complete
- [ ] Absolute changes, percentages, and denominators are shown together
- [ ] Citywide results are checked against subgroup patterns
- [ ] Applications are not described as completed homes
- [ ] Null and contradictory results remain in the analysis record
- [ ] Residual biases are stated in the final summary and presentation
