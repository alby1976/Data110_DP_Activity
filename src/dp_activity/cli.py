"""Command-line entry point for the development-permit pipeline.

This module defines the user-facing command entry point and keeps dependency assembly at
the application boundary.

Design Pattern:
    Composition Root and Command.

Pattern Rationale:
    The CLI is the single place that assembles concrete dependencies, then dispatches
    the user's selected command to the appropriate workflow.

Typical Usage:
    Invoke main() through the module entry point to dispatch a configured project
    workflow.

Implementation Outline:
    1. Build an argument parser with commands such as download, profile, analyse, and run.
    2. Accept an optional settings-file path; default to config/settings.yaml.
    3. Load and validate configuration.
    4. Construct repositories, pipeline stages, analyses, and exporters.
    5. Execute the requested command.
    6. Print a short success summary; convert expected project errors to friendly messages.
    7. Return a non-zero exit code on failure.
"""

from __future__ import annotations

from collections.abc import Sequence


def build_parser():
    """Create and return the project's command-line parser.

    Returns:
        The configured argument parser.

    Raises:
        NotImplementedError: The scaffolded behavior has not yet been implemented.
    """
    # TODO: Create argparse.ArgumentParser and its subcommands/options.
    raise NotImplementedError


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected command and return a process exit code.

    Args:
        argv: Command-line arguments excluding the executable name, or None to read the
            process arguments.

    Returns:
        A process exit code; zero indicates success.

    Raises:
        NotImplementedError: The scaffolded behavior has not yet been implemented.
    """
    # TODO: Parse argv.
    # TODO: Load settings and configure logging.
    # TODO: Assemble dependencies rather than constructing them inside analysis classes.
    # TODO: Dispatch the command and report its outputs.
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
