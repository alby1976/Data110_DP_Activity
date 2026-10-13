# Presentation Plan

## 10-minute notebook presentation

The [presentation notebook](../notebooks/03_ten_minute_presentation.ipynb)
provides a Quarto Reveal.js presentation. Its eight main sections total
**7:40**, with a **2:00** live Power BI demonstration and **0:20** transition
buffer for a **10:00** talk. Preparation and appendix questions are outside
that budget. Timings appear in presenter notes, not slide titles. The original slide
outline below remains a shorter alternative for a deck.

| Section | Topic | Time | Cumulative |
|---:|---|---:|---:|
| 1 | Question and comparison windows | 0:40 | 0:40 |
| 2 | Policy context and application activity | 0:45 | 1:25 |
| 3 | Source data and observational design | 1:00 | 2:25 |
| 4 | Cleaning, classification, and validation | 1:00 | 3:25 |
| 5 | Volume, exposure rates, and complete seasons | 1:15 | 4:40 |
| 6 | Residential type counts and shares | 1:00 | 5:40 |
| 7 | Community changes and processing eligibility | 1:10 | 6:50 |
| Demo | Overview, Development Type & Processing, Geography | 2:00 | 8:50 |
| 8 | Conclusions, safeguards, and remaining uncertainty | 0:50 | 9:40 |
| Buffer | Title, transitions, or pauses | 0:20 | 10:00 |

Install the project with `.[dev,parquet,excel,notebook]`, using `environment.yml`
or `requirements-dev.txt`, and select that interpreter in PyCharm. The `notebook`
extra provides IPython and ipykernel; version pins live in `pyproject.toml`.
The Conda environment includes Quarto CLI 1.9.38; Power BI Desktop is installed separately.
Use the project interpreter and run all cells before presenting. The notebook
requires the pinned `development_permits_residential_20261013_001726.parquet`
snapshot and its adjacent metadata sidecar under `data/raw`. Preparation checks
checksum, dataset/query identity, coverage, address-exclusion reconciliation,
schema, and analytical totals, then calls reusable project analyses. It makes
no permit downloads or data exports and uses source community/ward values.
Quarto separately renders the saved notebook output into an HTML slide deck.

The Conda specification installs **Quarto CLI 1.9.38** from conda-forge.
Create the environment with `conda env create --file environment.yml`, or update
an existing environment with `conda env update --file environment.yml`.
Activate it before rendering so the environment's Quarto executable is on PATH:

```powershell
conda activate data110-dp-activity
quarto --version
quarto render
```

Run and save all notebook cells in PyCharm before `quarto render`. The
`pyproject.toml` package and `requirements-dev.txt` do not install Quarto.
For a standard virtual environment, install the
[Quarto CLI](https://quarto.org/docs/get-started/) separately.

If `quarto` is not recognized, confirm the Conda environment is activated and
updated, then reopen the terminal. `Get-Command quarto` shows the executable
selected on Windows. If a separate workstation installation also exists,
check `quarto --version` to confirm which installation is being used.

The repository's `_quarto.yml` renders only the presentation notebook and writes
`reports/presentation/notebooks/03_ten_minute_presentation.html` plus supporting
assets. Open that HTML file in a browser. Keep its accompanying files together
when copying the deck. `S` opens speaker view, `F` enables fullscreen, and `Esc`
shows the overview. Presenter notes use Quarto's `.notes` blocks; preparation
cells use `include: false` and audience code cells use `echo: false`.

Rendering does not execute Python: the notebook's saved outputs are the source
of displayed results. Rerun all notebook cells after changing data or settings,
then render again. The `.quarto` cache and generated deck are ignored by Git.
No hosting or publishing is performed by these commands.

The [Quarto configuration](../_quarto.yml) selects the notebook, Reveal.js
theme, slide dimensions, output location, and saved-output rendering behavior.
[Presentation CSS](../notebooks/presentation.css) sizes headings, tables,
text output, and charts. These presentation settings are separate from the
analysis definitions in `config/settings.yaml`. Dense slides and the appendix
support scrolling; check them at the display size used for delivery.

If figures or findings are missing or stale, rerun all ten code cells in the
notebook and save it before rendering. Rendering alone does not recalculate
results. If copied slides lose styling or images, copy the complete generated
`reports/presentation/` directory, including its assets and reference files.
Keep the eight main sections and live demo within the talk and the appendix outside it.

The notebook calculates its findings rather than hard-coding summary totals.
It includes a monthly exposure-rate chart, complete-season rate table,
residential-type count chart, type/share comparison table, ranked community
change chart, and eligible processing-duration summaries. The community chart
shows only the ten largest absolute changes among known communities with
adequate baselines; the full geography results remain in the exploratory notebook.

Present sections 1–7, switch to Power BI at 6:50, and return to section 8 by
8:50. The notes contain exact spoken scripts; presenter cues and bracketed
actions are not spoken. The demo visits Overview, Development Type & Processing,
and Geography. Open the report before the talk, clear filters, and prepare static
backup screenshots. If behind schedule, show Overview and Geography only.
Keep setup and appendix output outside the timed talk. Rehearse twice; target
durations are guidance and do not guarantee a 10-minute delivery. If the course
requires questions within the same ten minutes, shorten the conclusion or use
the shorter deck outline below. The notebook is the editable source; the
rendered Reveal.js deck is the presentation artifact. Seasonal detail and full
type/share tables appear in the appendix to keep the main slides concise.

After changing inputs, settings, or classification rules, rerun all cells and
review warnings before delivery. Applications are not dwelling units, geography
uses source values, recent decisions have incomplete follow-up, and the design
does not establish a causal policy effect. Independent classification review,
sensitivity scenarios, and Power BI reconciliation remain outstanding.

Verification: all ten code cells completed successfully on October 12, 2026;
the three charts were visually inspected. The pinned run reports 9,856 Before,
7,603 During, and 556 contextual post-repeal residential applications. During
has 22.86% fewer applications and a 22.54% lower rate per 30 exposed days.
This is notebook verification, not a full test-suite run or timed rehearsal.
Quarto 1.10.19 rendered the HTML deck successfully with ten slides (title,
eight main sections, appendix), eight presenter-note blocks, and three local
chart images. Preparation output and Python source are hidden in the deck.
After installation, the persistent `quarto` command reported version 1.10.19
and rendered the notebook successfully from the repository root.
The rendered structure and image paths were checked; browser visual inspection
was unavailable because the connected browser blocks local file URLs.

## Alternative shorter deck

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
- name the principal risks: confounding, classification error, and incomplete recent cases.

### 4. From Raw Data to Analysis

- compact workflow graphic;
- two or three representative cleaning decisions;
- residential and rezoning-relevant classification method;
- validation result, not a screenshot of fifty lines of code.
- one concise example showing how a bias-control step changed or tested the analysis.

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
- mitigations actually performed and the biases that remain;
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
- [ ] Bias mitigations are supported by results or audit evidence, not merely promised
- [ ] Null, mixed, or contradictory findings have not been omitted
