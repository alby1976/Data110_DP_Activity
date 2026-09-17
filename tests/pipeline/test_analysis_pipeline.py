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

from conftest import implemented

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


def test_pipeline_returns_named_results() -> None:
    """Verify that pipeline returns named results."""
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
