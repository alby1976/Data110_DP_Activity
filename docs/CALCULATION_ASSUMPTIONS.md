# Calculation Assumptions and Simplifications

This document records the choices that keep the development-permit analysis
manageable and reproducible. These are analytical conventions, not claims that
the underlying development process is simple or that source records are perfect.
It describes the implemented calculations and committed configuration as of
September 23, 2026. Planned work is identified separately.

For calculation details, see [Methodology](METHODOLOGY.md); for field definitions,
see [Data Dictionary](DATA_DICTIONARY.md). The consequences and mitigation work
are expanded in [Biases and Mitigation](BIAS_AND_MITIGATION.md).

## 1. Population and unit of counting

| Assumption or simplification | Why it is used | Consequence for interpretation |
|---|---|---|
| One included source record contributes one application to counts. | Provides a consistent unit without linking records into physical projects. | Counts are not dwelling units, completed homes, or necessarily distinct projects. Analysis strategies do not deduplicate identifiers; duplicate findings must be investigated before accepting totals. |
| The study population is published development-permit applications. | Uses one accessible administrative source. | It does not represent all construction, building permits, unsubmitted proposals, or housing demand. |
| Residential inclusion is determined by `IncludeResidential` from the rule classifier. | Gives all implemented summaries a reproducible population definition. | Headline counts depend on classification choices; they do not establish the true residential population independently. |
| Source fields describe the frozen snapshot at retrieval. | Avoids reconstructing the history of every mutable administrative field. | Current status, decisions, and geography may differ from their values when an application was submitted. Snapshot consistency is not proof of source accuracy or completeness. |

## 2. Dates, policy windows, and exposure

| Assumption or simplification | Why it is used | Consequence for interpretation |
|---|---|---|
| `applied_date` assigns an application to a study period. | Gives each application one primary period without modelling planning lead time. | The application may have been conceived under an earlier policy and decided under a later one. Decision dates do not reassign the primary period. |
| Before is August 6, 2022–August 5, 2024; During is August 6, 2024–August 3, 2026. Endpoints are inclusive. | Uses explicit policy-related boundaries from the project configuration. | The windows are nearly equal, not exactly equal. Raw differences and exposure-adjusted rates answer different questions. |
| Early Post-Repeal begins August 4, 2026 and is contextual. | Keeps recent activity available without making it an equivalent third primary period. | Even a complete season within that period does not make the whole period comparable to the primary windows. |
| Calculations use source calendar dates, preserving the local date written in an ISO timestamp. | Avoids time-of-day and timezone conversion changing period membership. | These are calendar-day calculations, not elapsed-hour measurements. |
| Exposure includes every calendar day in the observed window, including weekends, holidays, and days with no applications. | Provides a simple, consistent denominator. | Rates are not permits per business day or per day the permitting office was open. |
| Configured exposure is treated as covered by the supplied snapshot. | Allows zero-activity months and seasons to be generated independently of observed records. | A zero means no included record in that interval; it is not evidence that the source had no publication gap. Snapshot coverage must be checked separately. |
| Open-ended windows need an explicit observation cutoff. | Prevents treating the last application date or today's date as evidence of coverage. | The CLI uses the UTC retrieval date from the snapshot sidecar, or an explicit `--observation-end YYYY-MM-DD` override, for season/processing features and volume/seasonal analyses. Missing or invalid metadata requires the override. Retrieval is a coverage convention, not proof of publication completeness. |
| Exploratory analysis without configured windows does not establish full exposure. | Allows inspection without inventing observation boundaries. | Exposure-based rates remain null. Observed seasons cannot establish unobserved zero-activity seasons. |

## 3. The standardized 30-day rate

Implemented period, monthly, and seasonal outputs use:

```text
DP_Rate30 = PermitCount / ExposureDays × 30
```

`PermitCount` is the number of included residential application records. The
factor 30 is a fixed reporting unit: **a standardized 30-day interval**, not the
actual length of every calendar month.

- Exposure days use inclusive window boundaries and any explicit observation
  cutoff. A one-day window has one exposed day.
- Zero permits over positive exposure give a rate of zero. Unknown or
  nonpositive exposure gives null, not zero or infinity.
- For example, 10 included applications in 15 exposed days give a rate of
  20 applications per 30 days.
- This is a rescaling of an observed average. It does **not** require applications
  to occur uniformly each day and does not predict the next 30 days. Using it as
  a forecast would add an untested assumption that the observed intensity persists.
- Pooled rates for disjoint time intervals use summed counts divided by summed
  exposure. They are not unweighted averages of individual rates. The implemented
  like-calendar-month table includes partial months in this pooled rate; unknown
  contributing exposure leaves the pooled rate unknown.
- Geography or type groups sharing a time window must not multiply its exposure
  when combined. Likewise, period totals must not be added to their monthly rows.

The adjustment handles unequal numbers of exposed days. It does not remove
seasonality, publication delays, confounding, or the instability of a short window.
The existing `AbsoluteChange` and `PercentChange` fields compare counts; adding
`DP_Rate30` does not turn those fields into changes in rates.

## 4. Seasons and summary statistics

| Assumption or simplification | Why it is used | Consequence for interpretation |
|---|---|---|
| Seasons are meteorological: Winter Dec–Feb, Spring Mar–May, Summer Jun–Aug, Fall Sep–Nov. | Gives a repeatable calendar classification without weather data. | It does not measure actual weather or construction conditions in a particular year. Winter remains one cross-year season. |
| A complete season must fit inside its own policy window and known observation horizon. | Prevents combining fragments across a policy boundary. | Two partial summer fragments are not merged into one complete policy-period observation. |
| Complete, partial, and unknown seasons are reported separately. | Keeps the main comparison simple while preserving context. | Unknown is not treated as false or complete. Complete-season selection changes the time coverage and must be disclosed. |
| Monthly means and medians include configured zero-activity months. | Avoids reporting only active months. | Ordinary monthly count summaries are not normalized for unequal month lengths or partial months; use `DP_Rate30` for a day-based rate. |
| `MeanCompleteMonthlyCount` uses complete months only. | Supports like-calendar-month inspection with known full coverage. | Its population differs from pooled `DP_Rate30`, which also includes known partial-month exposure. |

## 5. Classification, missing values, and geography

| Assumption or simplification | Why it is used | Consequence for interpretation |
|---|---|---|
| Enabled classification rules run in priority/rule-ID order; the first match determines the outcome. | Makes text-based classification deterministic without a statistical model. | Overlapping rules can affect results. Recorded matches and conflicts support review but do not prove accuracy. |
| Matching is case-insensitive under the committed settings. | Reduces differences caused only by letter case. | It does not resolve synonyms, ambiguous descriptions, or mixed-use applications. |
| Unmatched records are flagged for review and have residential inclusion and relevance set to false. | Avoids guessing an affirmative classification without a matching rule. | This can omit genuine residential applications. Included records already marked for review stay included; review status alone does not override the inclusion flag. |
| Included missing housing-type labels are reported as Unknown in type summaries. | Preserves residential denominators without inventing a type. | Unknown is a reporting category, not a verified development form. |
| Geography analysis groups trimmed community/ward labels, retaining missing groups. | Avoids a separate boundary-matching or geocoding model. | It does not harmonize spelling, historical ward boundaries, stable community codes, or allocate multi-location applications across places. |
| Geography shares include records with missing geography in the residential denominator. | Prevents incomplete mapping from silently shrinking the population. | Mapped records alone do not sum to the entire population. Missing community and ward counts may overlap. |
| Baselines below 5 records receive a warning under the committed configuration. | Provides a transparent indicator of unstable percentage changes. | Five is a reporting choice, not a statistical significance threshold. Small groups remain present; zero-baseline percentage changes are null. |

Missing values are not assumed to be random. Keeping a missing group or audit
count makes missingness visible; it does not correct missing-data bias.

## 6. Processing-time calculations

| Assumption or simplification | Why it is used | Consequence for interpretation |
|---|---|---|
| `ProcessingDays = decision_date - applied_date`, using calendar dates. | Uses available endpoints without reconstructing administrative workflow. | The interval includes weekends and pauses and is not staff working time, construction time, or time to permit release. |
| Statistics use residential records flagged valid by the feature stage; the current minimum is zero days. | Excludes missing/invalid intervals and negative durations while allowing same-day decisions. | Valid observed cases can differ systematically from unresolved cases. Negative values remain audit evidence rather than being changed to zero. |
| Median, mean, and linearly interpolated quartiles summarize valid durations. | Uses familiar descriptive statistics without fitting a distribution. | Quartiles and means can be fractional even though individual durations are whole calendar days. IQR is Q3 minus Q1. |
| Pending means a usable application with a genuinely missing decision, subject to the explicit cutoff when supplied. | Provides an auditable proxy when reconstructing official status history is impractical. | It is not an official pending-status determination. Malformed decisions are not treated as pending. |
| Censored and otherwise ineligible records are counted but do not enter duration statistics. | Keeps the main calculation interpretable without survival modelling. | The summaries do not correct right-censoring. Minimum-follow-up eligibility is not implemented. |
| Audit reasons may overlap; unavailable optional flags yield null audit counts. | Preserves separate evidence without inventing a mutually exclusive classification. | Pending, censored, missing-date, and other counts must not be added as a unique exclusion total. |

## 7. Scope limits and choices still requiring implementation

`SensitivityAnalysis` now evaluates injected named scenarios against an explicit
reference. Each scenario returns the same scalar metric under a caller-defined
alternative. All results are retained, including weaker or missing results;
each scenario receives an independent input copy. AbsoluteChange is the signed
difference from the reference, and PercentChange uses the absolute reference
magnitude as its denominator. Zero/missing reference values leave percentage
changes null. These comparisons do not establish statistical significance.
The CLI currently supplies no scenarios and therefore produces an empty
sensitivity table; this is not evidence that study sensitivity checks were run.

The project is descriptive. It does not assume that all observed change was
caused by rezoning, that applications are independent physical developments, or
that review flags establish classification accuracy. Exposure normalization is
not a substitute for a causal model or a sensitivity analysis.

The Power BI exporter now persists clean permits, supplied analysis and validator
tables, a record-based reconciliation table, and an overlapping Boolean-flag bias
audit. Reconciliation totals are calculated from permits independently of analysis
summaries; exporting them does not establish agreement with Power BI. Missing audit
flags have null counts, and known true counts are reported beside unknown counts.
The audit covers supplied flags, not every bias or source-quality concern.
Dates use ISO text and missing values remain missing. Files are atomic individually;
an I/O failure can leave earlier files from the same export. No complete run
provenance manifest is assembled yet.

The following remain outstanding in the current checkout and must not be
described as completed safeguards:

- minimum-follow-up eligibility and configuration/execution of study-specific
  sensitivity comparisons (the named-scenario runner is implemented);
- a policy for stopping the pipeline on fatal validation reports; collecting a
  report currently does not itself halt execution;
- full run provenance, full pipeline smoke testing, and Python/Power BI
  reconciliation;
- CLI integration of the implemented chart factory with explicit policy boundaries;
- independent classification review and investigation of missing, duplicate, or
  geographically ambiguous source records before accepting final findings.

When an assumption changes, update this document, the corresponding methodology
and field definitions, and behavior tests. Record the configuration and source
snapshot used so the revised results can be reproduced.

`ChartFactory.monthly_volume` plots supplied residential record counts, not rates.
It does not infer zero activity for missing months: missing months break lines,
while supplied zero counts remain zero. Partial exposure has triangle markers;
unknown exposure has cross markers. Each policy period is a separate series.
Exact policy boundaries are optional caller-supplied dates, never inferred from
the first application. Charts do not adjust for unequal month lengths or establish
policy causation. Figure saving is explicit and supports PNG, SVG, and PDF.
