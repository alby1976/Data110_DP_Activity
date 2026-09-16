# Presentation Plan

Target length: **8–9 minutes**, leaving time for transitions or a brief question within the 10-minute limit.

## Slide outline

| Slide | Title | Main point | Target time |
|---:|---|---|---:|
| 1 | Development Permit Activity | Introduce the question and the two comparison periods | 0:40 |
| 2 | Why This Question Matters | Explain the policy timeline and why permit activity is useful | 0:55 |
| 3 | Data and Study Design | Identify dataset, unit of analysis, dates, and observational design | 1:05 |
| 4 | From Raw Data to Analysis | Show Python cleaning, classification, validation, and export workflow | 1:05 |
| 5 | Permit Volume Over Time | Present monthly, seasonal, and before/during comparisons | 1:15 |
| 6 | What Types Changed? | Compare counts and shares by residential type | 1:05 |
| 7 | Where and How Long? | Show geography and median processing-time findings | 1:20 |
| 8 | Conclusions and Limits | Answer the question, state limitations, and avoid causal overclaiming | 1:10 |

Estimated total: **8:35**.

## What each slide needs

### 1. Development Permit Activity

- project title;
- author and course;
- one-sentence research question;
- simple Before versus During date strip.

### 2. Why This Question Matters

- August 6, 2024 implementation;
- August 4, 2026 repeal changes effective;
- one sentence explaining that a DP application is not the same as a completed home;
- neutral language about examining activity, not proving policy effects.

### 3. Data and Study Design

- City of Calgary dataset `6933-unw5`;
- one permit application per row;
- primary period based on `AppliedDate`;
- key fields and final analytical sample size;
- limitation banner: observational comparison.

### 4. From Raw Data to Analysis

- compact workflow graphic;
- two or three representative cleaning decisions;
- residential and rezoning-relevant classification method;
- validation result, not a screenshot of fifty lines of code.

### 5. Permit Volume Over Time

- one main monthly chart;
- a concise seasonal comparison using Fall (Sep–Nov), Winter (Dec–Feb), Spring (Mar–May), and Summer (Jun–Aug);
- period boundary annotation;
- Before and During totals/monthly averages;
- a visible note where a season is incomplete or split by a policy boundary;
- one plain-language takeaway.

### 6. What Types Changed?

- count comparison by standardized residential type;
- share comparison to distinguish growth from mix change;
- call out the most important result only.

### 7. Where and How Long?

- community map or ranked community chart;
- median processing days with valid record count;
- warn where small baseline counts inflate percentages.

### 8. Conclusions and Limits

- direct answer to each important research question;
- two or three strongest findings;
- two or three major limitations;
- final sentence: what the evidence supports and what it does not.

## Delivery notes

- Rehearse from speaker notes, not paragraphs on the slides.
- Aim for one claim per visual.
- State whether counts refer to applications, decisions, or approvals.
- Say **associated with** or **differed**, not **caused**.
- If demonstrating Power BI live, keep a static backup screenshot in the deck. Live demos have a mischievous sense of timing.
- Put detailed methods and secondary tables in appendix slides, outside the main eight-slide path.

## Final presentation checklist

- [ ] All displayed numbers match Python and Power BI
- [ ] Source and retrieval date appear in the deck
- [ ] Policy dates are cited
- [ ] Incomplete post-repeal data is clearly labelled
- [ ] Every chart has a descriptive title and readable axis labels
- [ ] Colour choices are consistent and accessible
- [ ] Slides fit within 10 minutes during two timed rehearsals
- [ ] PDF export and PowerPoint file both open correctly
- [ ] Static backup exists for any live dashboard demonstration
