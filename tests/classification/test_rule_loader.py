from conftest import REPOSITORY_ROOT, implemented

from dp_activity.classification.rule_loader import RuleLoader


def test_rules_are_enabled_unique_and_sorted() -> None:
    rules = implemented(
        RuleLoader().load,
        REPOSITORY_ROOT / "config/classification_rules.csv",
    )
    assert rules[0].rule_id == "HF-001"
    assert len({rule.rule_id for rule in rules}) == len(rules)
    assert [(rule.priority, rule.rule_id) for rule in rules] == sorted(
        (rule.priority, rule.rule_id) for rule in rules
    )
    assert all(rule.enabled for rule in rules)

