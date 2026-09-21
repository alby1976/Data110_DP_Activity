"""Tests for analysis pipeline.

This module verifies the documented contracts and edge cases of the analysis pipeline
component.

Design Pattern:
    None

Pattern Rationale:
    The module contains pytest verification code and does not intentionally implement an
    application design pattern.

Typical Usage:
    Pytest discovers this module and executes its focused unit tests with small
    deterministic inputs.
"""

from dp_activity.pipeline.analysis_pipeline import AnalysisPipeline, PipelineResult


class StubRepository:
    """Provide a minimal raw-data repository test double.

    The stub returns one deterministic permit record so pipeline orchestration can be
    tested without filesystem input.
    """

    def load_snapshot(self, path):
        """Return a minimal permit snapshot for pipeline tests.

        Args:
            path: Snapshot or figure path supplied by the caller.

        Returns:
            A one-record permit collection.
        """
        return [{"permit_number": "DP1"}]


class IdentityStage:
    """Provide no-op cleaning and classification test methods.

    The stub preserves its input so the pipeline test isolates orchestration behavior.
    """

    def clean(self, rows):
        """Return rows unchanged for pipeline isolation.

        Args:
            rows: Permit records passed through the test stage.

        Returns:
            The unmodified row collection.
        """
        return rows

    def classify(self, rows):
        """Return rows unchanged for pipeline isolation.

        Args:
            rows: Permit records passed through the test stage.

        Returns:
            The unmodified row collection.
        """
        return rows


class StubExporter:
    """Provide deterministic export paths for pipeline tests.

    The stub avoids filesystem output while preserving the exporter contract.
    """

    def export(self, permit_table, analysis_tables, validation_tables):
        """Return a deterministic output mapping for pipeline tests.

        Args:
            permit_table: Permit-level table supplied by the pipeline.
            analysis_tables: Analysis outputs supplied by the pipeline.
            validation_tables: Validation outputs supplied by the pipeline.

        Returns:
            A logical output name mapped to a deterministic filename.
        """
        return {"clean": "permits.csv"}


class StubAnalysis:
    """Provide a deterministic analysis strategy for pipeline orchestration tests."""

    name = "stub_analysis"

    def run(self, permits):
        """Return one named analysis table.

        Args:
            permits: Permit records supplied by the pipeline.

        Returns:
            A named table mapping that preserves the input for assertion.
        """
        return {"summary": permits}


def test_pipeline_constructor_stores_injected_collaborators() -> None:
    """Verify that constructor injection defines the pipeline graph."""
    source_repository = StubRepository()
    cleaner = IdentityStage()
    classifier = IdentityStage()
    feature_builders = [lambda rows: rows]
    validators = [lambda rows: []]
    analyses = [object()]
    exporter = StubExporter()

    pipeline = AnalysisPipeline(
        source_repository=source_repository,
        cleaner=cleaner,
        classifier=classifier,
        feature_builders=feature_builders,
        validators=validators,
        analyses=analyses,
        exporter=exporter,
    )
    feature_builders.append(lambda rows: rows)
    validators.append(lambda rows: [])
    analyses.append(object())

    assert pipeline.source_repository is source_repository
    assert pipeline.cleaner is cleaner
    assert pipeline.classifier is classifier
    assert len(pipeline.feature_builders) == 1
    assert len(pipeline.validators) == 1
    assert len(pipeline.analyses) == 1
    assert pipeline.exporter is exporter


def test_pipeline_returns_named_results() -> None:
    """Verify that pipeline returns named results."""
    def add_feature(rows):
        """Add one derived row so feature-builder ordering is visible."""
        return [*rows, {"permit_number": "DP2"}]

    def validation_report(rows):
        """Return a validation report derived from feature-enriched rows."""
        return {"row_count": len(rows)}

    pipeline = AnalysisPipeline(
        source_repository=StubRepository(),
        cleaner=IdentityStage(),
        classifier=IdentityStage(),
        feature_builders=[add_feature],
        validators=[validation_report],
        analyses=[StubAnalysis()],
        exporter=StubExporter(),
    )
    result = pipeline.run("snapshot.csv")
    assert isinstance(result, PipelineResult)
    assert result.cleaned_permits == [
        {"permit_number": "DP1"},
        {"permit_number": "DP2"},
    ]
    assert result.validation_reports["validation_report"] == {"row_count": 2}
    assert result.analysis_tables["summary"] == result.cleaned_permits
    assert result.output_paths["clean"] == "permits.csv"
