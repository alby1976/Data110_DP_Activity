"""Development-permit activity analysis package.

This package groups the components used to acquire, prepare, analyze, validate,
and export development-permit data. Its top-level API exposes the configuration
loader and settings types used to assemble those components. Importing the
package does not load settings or start the analysis workflow.

Design Pattern:
    None.

Pattern Rationale:
    The package initializer organizes related components but does not itself implement
    an application design pattern.

Typical Usage:
    Import load_config and the settings types from dp_activity when assembling
    the development-permit analysis workflow. Import specialized components
    from their own subpackages.

Examples:
    >>> from pathlib import Path
    >>> from dp_activity import load_config
    >>> config = load_config(Path("config/settings.yaml"))
"""

from .config import LogArchiveConfig, ProjectConfig, StudyPeriod, load_config

__all__ = [
    "LogArchiveConfig",
    "ProjectConfig",
    "StudyPeriod",
    "load_config",
]
