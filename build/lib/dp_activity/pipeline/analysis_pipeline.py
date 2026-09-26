"""Orchestrate the complete analysis without hiding stage boundaries.

This module loads an existing raw snapshot and coordinates preparation, validation,
analysis, and export stages. Acquisition is handled separately by the download command.

Design Pattern:
    Facade, Dependency Injection, and Pipes and Filters.

Pattern Rationale:
    The facade exposes one run() operation while injected collaborators form explicit
    processing stages that can be replaced with test doubles.

Typical Usage:
    Construct the pipeline with concrete collaborators and run it for one immutable
    snapshot.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
import re
from typing import Any

NAME_TOKEN_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


@dataclass
class PipelineResult:
    """Collect the named outputs of a successful pipeline run.

    This result object keeps transformed data, analysis tables, validation reports,
    and persisted paths together for downstream use.

    Attributes:
        cleaned_permits: Final permit-level table used by analyses.
        analysis_tables: Stable output names mapped to analytical result tables.
        validation_reports: Validator names mapped to structured findings.
        output_paths: Logical output names mapped to persisted locations.
    """

    cleaned_permits: Any
    analysis_tables: dict[str, Any]
    validation_reports: dict[str, Any]
    output_paths: dict[str, Any]


class AnalysisPipeline:
    """Coordinate injected collaborators in a visible processing sequence.

    This class is a Facade over a Pipes-and-Filters workflow. Constructor injection
    keeps concrete repositories, transformations, validators, analyses, and exporters
    replaceable for testing and extension.

    Attributes:
        source_repository: Persistence boundary used to load raw snapshots.
        cleaner: Stage that standardizes source records.
        classifier: Stage that assigns auditable permit classifications.
        feature_builders: Ordered transformations that derive analytical fields.
        validators: Ordered validation services.
        analyses: Interchangeable analysis strategies.
        exporter: Boundary that persists finalized outputs.
    """

    def __init__(
        self,
        *,
        source_repository: Any,
        cleaner: Any,
        classifier: Any,
        feature_builders: list[Any],
        validators: list[Any],
        analyses: list[Any],
        exporter: Any,
    ) -> None:
        """Store injected pipeline collaborators without constructing concrete services.

        Args:
            source_repository: Persistence boundary used to load immutable raw snapshots.
            cleaner: Transformation stage that standardizes source records.
            classifier: Transformation stage that applies classification rules.
            feature_builders: Ordered callables that derive analytical fields.
            validators: Ordered validation services or callables.
            analyses: Ordered analysis strategies.
            exporter: Persistence boundary that exports finalized outputs.

        Note:
            The sequence arguments are copied so later caller-side mutations do not
            change the configured pipeline graph.
        """
        self.source_repository = source_repository
        self.cleaner = cleaner
        self.classifier = classifier
        self.feature_builders = list(feature_builders)
        self.validators = list(validators)
        self.analyses = list(analyses)
        self.exporter = exporter

    def run(self, snapshot_path: Any) -> PipelineResult:
        """Run one reproducible analysis.

        Args:
            snapshot_path: Path identifying the immutable source snapshot to process.

        Returns:
            Named transformed data, reports, analyses, and output paths.

        Raises:
            TypeError: An analysis strategy does not return a mapping of output names
                to result tables.
            ValueError: Two analysis strategies return the same output name.

        Note:
            Collaborator exceptions propagate to the caller, including
            NotImplementedError from unfinished stages. Validation reports are
            collected without inspecting their severity; only a raised exception
            stops execution. Export side effects are not rolled back on failure.
        """
        permits = self.source_repository.load_snapshot(snapshot_path)
        permits = self.cleaner.clean(permits)
        permits = self.classifier.classify(permits)

        for feature_builder in self.feature_builders:
            permits = feature_builder(permits)

        validation_reports = self._run_validators(permits)
        analysis_tables = self._run_analyses(permits)
        output_paths = self.exporter.export(
            permits,
            analysis_tables,
            validation_reports,
        )

        return PipelineResult(
            cleaned_permits=permits,
            analysis_tables=analysis_tables,
            validation_reports=validation_reports,
            output_paths=output_paths,
        )

    def _run_validators(self, permits: Any) -> dict[str, Any]:
        """Run each injected validator and collect reports by stable names.

        Args:
            permits: Classified, feature-enriched permit table.

        Returns:
            Validator names mapped to their structured reports.
        """
        reports: dict[str, Any] = {}
        for index, validator in enumerate(self.validators, start=1):
            name = self._unique_key(
                reports,
                self._component_name(validator, fallback=f"validator_{index}"),
            )
            reports[name] = validator(permits)
        return reports

    def _run_analyses(self, permits: Any) -> dict[str, Any]:
        """Run analysis strategies and merge their named result tables.

        Args:
            permits: Classified, feature-enriched permit table.

        Returns:
            Stable output names mapped to analysis result tables.

        Raises:
            TypeError: An analysis strategy does not return a mapping.
            ValueError: Multiple analyses return the same output name.
        """
        tables: dict[str, Any] = {}
        for analysis in self.analyses:
            result = analysis.run(permits)
            if not isinstance(result, Mapping):
                name = self._component_name(analysis, fallback="analysis")
                raise TypeError(f"Analysis '{name}' must return a mapping of tables.")

            for output_name, table in result.items():
                if output_name in tables:
                    raise ValueError(f"Duplicate analysis output name: {output_name}")
                tables[output_name] = table
        return tables

    @classmethod
    def _component_name(cls, component: Any, *, fallback: str) -> str:
        """Return a stable snake_case name for an injected component.

        Args:
            component: Callable or strategy object to name.
            fallback: Name used when the component has no useful identifier.

        Returns:
            A lowercase identifier suitable for result dictionaries.
        """
        explicit_name = getattr(component, "name", None)
        if isinstance(explicit_name, str) and explicit_name.strip():
            return cls._to_snake_case(explicit_name)

        target = component
        if isinstance(component, partial):
            target = component.func

        owner = getattr(target, "__self__", None)
        if owner is not None:
            return cls._to_snake_case(owner.__class__.__name__)

        function_name = getattr(target, "__name__", None)
        if isinstance(function_name, str) and function_name != "<lambda>":
            return cls._to_snake_case(function_name)

        class_name = component.__class__.__name__
        if class_name and class_name != "object":
            return cls._to_snake_case(class_name)

        return fallback

    @staticmethod
    def _unique_key(existing: dict[str, Any], requested_key: str) -> str:
        """Return a dictionary key that does not overwrite an existing report.

        Args:
            existing: Dictionary that will receive the key.
            requested_key: Preferred key for the report.

        Returns:
            The requested key or a numbered variant.
        """
        if requested_key not in existing:
            return requested_key

        counter = 2
        while f"{requested_key}_{counter}" in existing:
            counter += 1
        return f"{requested_key}_{counter}"

    @staticmethod
    def _to_snake_case(value: str) -> str:
        """Convert a class or component name to snake_case.

        Args:
            value: Name to normalize.

        Returns:
            Lowercase snake_case text.
        """
        return NAME_TOKEN_PATTERN.sub("_", value.strip()).replace("-", "_").lower()
