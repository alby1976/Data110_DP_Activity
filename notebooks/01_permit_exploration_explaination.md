# Explanation of values in `01_permit_exploration.ipynb`

The notebook is an exploratory review of the frozen **Before** development-permit snapshot. The values shown are mostly **data-quality, provenance, cleaning, and classification summaries**. They describe the permit records in the downloaded file, not housing units built.

## 1. Settings table

The first displayed table shows which configured input the notebook is using.

| Field | Meaning |
|---|---|
| `dataset_id` | The Socrata dataset identifier being reviewed. |
| `study_period` | The configured policy/study period, such as `Before`. |
| `start_inclusive` | First date included in the Before period. |
| `end_inclusive` | Last date included in the Before period. |
| `primary_date_field` | The source date field used to decide whether a permit belongs in the period. |
| `rule_file` | Classification rules file used to classify permits. |
| `raw_formats` | Raw snapshot formats configured for downloads, such as `csv` and `parquet`. |

This table confirms that the notebook is reviewing the configured Before period using the configured classification rules.

## 2. Snapshot verification table

This table proves that the notebook loaded the intended frozen snapshot and that it matches the expected period and metadata.

| Field | Meaning |
|---|---|
| `study_period` | The period represented by the snapshot. |
| `first_application` | Earliest application date found in the snapshot. |
| `last_application` | Latest application date found in the snapshot. |
| `period_verified` | `True` means all checked application dates fall within the configured Before period. |
| `rows` | Number of permit records loaded. |
| `columns` | Number of fields/columns in the raw dataset. |
| `snapshot_sha256` | Cryptographic hash of the raw snapshot file. Used to prove the file did not change. |
| `checksum_verified` | `True` means the file hash matches its metadata sidecar. |
| `retrieved_at_utc` | When the snapshot was downloaded. |
| `selection` | Explains whether this is a full download or a sample. |
| `settings_sha256` | Hash of the settings file used for reproducibility. |
| `rules_sha256` | Hash of the classification rules file used for reproducibility. |

In plain language, this table says: the intended Before snapshot was loaded, its checksum is valid, and its dates fit the configured Before period.

## 3. Raw preview table

The preview table shows the first few raw permit records.

Typical columns:

| Column | Meaning |
|---|---|
| `permitnum` | Source permit identifier. |
| `applieddate` | Date the permit was applied for. |
| `category` | City/source permit category. |
| `proposedusedescription` | Source description of the proposed use. |
| `communityname` | Calgary community associated with the permit. |

This is only a quick sample of records, not a summary.

## 4. Source profile: row and column count

The profiler summary shows:

| Field | Meaning |
|---|---|
| `row_count` | Total number of loaded raw permit records. |
| `column_count` | Total number of fields in the raw dataset. |

These values describe the size of the raw Before snapshot.

## 5. Data types table

The `dtypes` table shows how pandas interpreted each source column.

| dtype | Meaning |
|---|---|
| `object` | Usually text/string-like values, or mixed values. |
| `int64` / `float64` | Numeric values. |
| `datetime64` | Parsed date/time values, if applicable. |
| `bool` | True/false values. |

Many raw Socrata-style columns may appear as `object` because dates, addresses, categories, and descriptions often arrive as strings.

## 6. Missingness table

The missingness table ranks columns by missing values.

| Field | Meaning |
|---|---|
| `column` | Column being checked. |
| `missing_count` | Number of rows where the value is null/missing. |
| `missing_percentage` | Percent of all rows missing that value. |

This only counts pandas-recognized nulls. Blank strings may remain as source evidence until cleaning.

## 7. Permit uniqueness and duplicate examples

These tables check whether permit identifiers are unique.

| Value | Meaning |
|---|---|
| Total permit records | Number of rows. |
| Unique permit numbers | Number of distinct permit IDs. |
| Duplicate count | Records sharing an identifier with another row. |
| Duplicate examples | Sample duplicate permit IDs and rows. |

Duplicates do not automatically mean errors. A permit may appear more than once depending on source structure, revisions, or repeated records.

## 8. Date ranges

The date range table shows minimum and maximum values for date fields.

| Column | Meaning |
|---|---|
| `applieddate` min/max | Earliest/latest application date. |
| `decisiondate` min/max | Earliest/latest decision date where present. |
| `completeddate` min/max | Earliest/latest completion date where present. |

This helps confirm whether loaded records fall inside the intended study window and whether other lifecycle dates behave as expected.

## 9. Source distributions

The notebook prints distributions for fields such as:

- `category`
- `proposedusedescription`
- `landusedistrict`
- `statuscurrent`

Each distribution table usually has:

| Field | Meaning |
|---|---|
| `value` | A unique source value. |
| `count` | Number of records with that value. |
| `percentage` | Share of all records with that value. |

These are source status/category counts, not analysis conclusions.

## 10. Cleaning comparison table

The cleaning comparison table compares missing values before and after cleaning.

| Field | Meaning |
|---|---|
| `column` | Cleaned or mapped column name. |
| `missing_count_before` | Missing values before cleaning. |
| `missing_count_after` | Missing values after cleaning. |
| `change` | Difference after cleaning. |

If `change` is `0`, cleaning renamed or standardized fields without changing missingness for that field.

## 11. Invalid flag table

The invalid flag table shows how many rows had invalid dates or coordinates after cleaning.

| Field | Meaning |
|---|---|
| `applied_date_invalid` | Rows where application date could not be parsed properly. |
| `decision_date_invalid` | Rows where decision date could not be parsed properly. |
| `latitude_invalid` | Rows with unusable latitude. |
| `longitude_invalid` | Rows with unusable longitude. |

A value of `0` means no invalid values were detected for that field.

## 12. “Preserved records and the original row index”

This message means cleaning did not drop, reorder, or duplicate records.

It confirms:

- raw row count equals cleaned row count,
- original row order/index was preserved,
- source table was not mutated.

## 13. Classification summary table

This table summarizes the classification results.

| Field | Meaning |
|---|---|
| `enabled_rules` | Number of classification rules loaded and enabled. |
| `records` | Number of records classified. |
| `matched` | Records that matched at least one rule. |
| `unmatched` | Records that matched no rule. |
| `needs_review` | Records that should be manually reviewed. |
| `overlapping_matches` | Records that matched more than the winning rule. |
| `included_residential` | Records classified as included residential records. |

Important interpretation:

- `matched` means a rule matched the record.
- `unmatched` means no rule matched.
- `needs_review` means the classification result is not considered final or fully validated.
- `overlapping_matches` may be expected when broad fallback rules overlap with more specific rules.
- `included_residential` is the count of records included in residential analysis.

## 14. Rule coverage table

The rule coverage table shows how many records each rule classified.

| Column | Meaning |
|---|---|
| `ClassificationRule` | Winning rule ID. |
| `ValidationStatus` | Confidence/status assigned to that rule. |
| `ClassificationNeedsReview` | Whether records using that rule require review. |
| `record_count` | Number of records where this rule won. |
| `matched_count` | Records matched by the rule. |
| `unmatched_count` | Usually records without a rule in unmatched groups. |
| `conflict_count` | Records where this winning rule had additional overlapping matches. |
| `additional_match_count` | Total number of non-winning additional rule matches. |
| `record_percentage` | Percent of all records classified by that winning rule. |

A rule with a high `record_count` is a common winning classification rule.

## 15. Residential type grouping table

This table groups records by final classification outputs.

| Column | Meaning |
|---|---|
| `ResidentialType` | Final assigned residential/non-residential type. |
| `IncludeResidential` | Whether this record should be included in residential analysis. |
| `ValidationStatus` | Status of the rule/classification. |
| `records` | Number of records in that group. |

Examples:

| ResidentialType | IncludeResidential | Meaning |
|---|---|---|
| `Single Detached` | `True` | Included as residential single-detached permits. |
| `Non-Residential` | `False` | Excluded from residential analysis. |
| `Review` | varies | Needs manual review. |
| `Secondary Suite` | `True` | Included as residential secondary suite permits. |

This table answers what types of records the classifier produced and how many are included or excluded.

## 16. Unmatched records table

The notebook prints unmatched records where no classification rule matched.

Columns shown may include:

| Column | Meaning |
|---|---|
| `permit_number` | Permit ID needing review. |
| `category` | Cleaned category. |
| `proposed_use_description` | Cleaned proposed use. |
| `description` | Source description text. |
| `raw_category` | Original source category before cleaning. |
| `raw_proposed_use_description` | Original source proposed use before cleaning. |
| `ClassificationRule` | Missing/NA because no rule matched. |
| `ValidationStatus` | Usually `unmatched`. |
| `ResidentialType` | Often assigned default review label. |
| `ClassificationNeedsReview` | `True` for unmatched records. |
| `ClassificationMatchedRules` | Empty because no rules matched. |

These records likely need a new classification rule, a data correction, or an explicit decision to leave them as review/excluded.

## 17. Needs review table

The notebook also prints records where `ClassificationNeedsReview` is `True`.

These are not necessarily wrong. They are records where the rule status or fallback classification says manual confirmation is needed.

Reasons may include:

- provisional rule,
- fallback rule,
- unmatched record,
- broad category requiring human review.

## 18. Potential overlaps table

This table shows records where more than one rule matched.

That does not automatically mean a conflict or error. The first enabled rule in priority/ID order wins, while later matches are retained as evidence.

Use this table to investigate whether the winning rule makes sense.

## 19. Rule coverage detail table

This table shows every configured rule and how often it matched.

| Column | Meaning |
|---|---|
| `rule_id` | Rule identifier from the classification CSV. |
| `priority` | Rule priority/order. |
| `field` | Field the rule checks. |
| `match_value` | Value/pattern the rule looks for. |
| `validation_status` | Confidence/review status assigned to the rule. |
| `winning_records` | Records where this rule was the final winning rule. |
| `all_matching_records` | Records where this rule matched, even if another rule won. |

A rule with `winning_records = 0` is not automatically bad. It may be shadowed by higher-priority rules, or the current snapshot may simply not contain matching records.

## 20. Description examples

The final displayed examples show common descriptions from the source data.

These examples help you understand what raw permit descriptions look like, such as:

- new residential construction,
- change of use,
- relaxations,
- additions,
- secondary suites,
- signs,
- commercial uses.

They are useful when deciding whether classification rules are catching the right text patterns.

## Main takeaway

The notebook shows that:

1. The loaded file is a verified Before-period raw snapshot.
2. The notebook is reviewing permit records, not completed housing units.
3. Cleaning preserves all records and checks dates/coordinates.
4. Classification covers nearly all records.
5. Some records need review or are unmatched.
6. Many records have overlapping rule matches, which can be expected when broad fallback rules exist.
7. The notebook is exploratory evidence, not proof of policy impact or housing completions.