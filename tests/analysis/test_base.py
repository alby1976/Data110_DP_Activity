import inspect

from dp_activity.analysis.base import Analysis


def test_analysis_is_an_abstract_contract() -> None:
    assert inspect.isabstract(Analysis)
    assert "run" in Analysis.__abstractmethods__

