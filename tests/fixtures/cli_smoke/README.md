# Frozen CLI smoke fixture

These seven records are invented test data, not City of Calgary records or study
findings. Dates exercise all three configured policy windows, both August policy
boundaries, a pending decision, a post-cutoff decision, missing geography, and a
review classification. The frozen observation cutoff is September 22, 2026.

Expected residential counts are Before=2, During=2, Early Post-Repeal=2; one
additional record is excluded. Valid residential processing counts are 2, 1, 1.
The January 2023 residential count is 1; February 2023 is an explicit zero month.
Early Post-Repeal September exposure is 22 days with one residential record.
All six residential records match rezoning-relevant rules in the committed rule
file. Classifier rules are intentionally not stubbed; policy changes that alter
these expectations require reviewing and updating this fixture's assertions.

Run `python -m pytest tests/test_cli_smoke.py -q`. The tests copy fixtures and
project configuration into isolated temporary directories, reject network use,
and invoke the actual CLI dispatch with real pipeline collaborators. CSV, JSON,
and Parquet exports are checked; Parquet requires the optional dependency.
Outputs stay in pytest temporary directories. No production snapshots or outputs
are changed. The suite also records the current collect-only validation behavior:
a reported failure does not yet stop export.
