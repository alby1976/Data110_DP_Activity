from conftest import implemented

from dp_activity.pipeline.analysis_pipeline import AnalysisPipeline, PipelineResult


class StubRepository:
    def load_snapshot(self, path):
        return [{"permit_number": "DP1"}]


class IdentityStage:
    def clean(self, rows):
        return rows

    def classify(self, rows):
        return rows


class StubExporter:
    def export(self, permit_table, analysis_tables, validation_tables):
        return {"clean": "permits.csv"}


def test_pipeline_returns_named_results() -> None:
    pipeline = implemented(
        AnalysisPipeline,
        source_repository=StubRepository(),
        cleaner=IdentityStage(),
        classifier=IdentityStage(),
        feature_builders=[],
        validators=[],
        analyses=[],
        exporter=StubExporter(),
    )
    result = implemented(pipeline.run, "snapshot.csv")
    assert isinstance(result, PipelineResult)
    assert result.cleaned_permits == [{"permit_number": "DP1"}]
    assert result.output_paths["clean"] == "permits.csv"

