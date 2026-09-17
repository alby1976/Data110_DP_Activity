import pandas as pd

from conftest import implemented

from dp_activity.classification.classifier import PermitClassifier
from dp_activity.classification.rule import ClassificationRule


def test_first_matching_rule_is_recorded() -> None:
    rule = ClassificationRule(
        "HF-001", "HousingForm", "proposedusedescription", "contains", "ROWHOUSE",
        True, "Rowhouse", True, 10, True, "validated_2026_sample", "test",
    )
    permits = pd.DataFrame({"proposed_use_description": ["New rowhouse building"]})
    classifier = PermitClassifier(
        [rule],
        {"proposedusedescription": "proposed_use_description"},
    )

    result = implemented(classifier.classify, permits)

    assert result.loc[0, "ClassificationRule"] == "HF-001"
    assert bool(result.loc[0, "IncludeResidential"]) is True
    assert result.loc[0, "ResidentialType"] == "Rowhouse"

