# Project Instructions

These instructions apply to the entire repository, including application code,
tests, fixtures, and Python utility scripts.

## Python Documentation Standard

For every Python source file created or modified in this project:

- Follow **PEP 257** conventions.
- Use **Google-style docstrings** for modules, classes, methods, and functions.
- Preserve existing program behavior when the task is documentation-only.
- Preserve existing type hints.
- Do not invent design patterns that are not actually present in the
  implementation.

Every Python module must begin with a module-level docstring using this
structure:

```python
"""Module summary.

Brief explanation of what this module does and its responsibility within
the application.

Design Pattern:
    <Design pattern intentionally used by this module, or "None".>

Pattern Rationale:
    Explain why this pattern is appropriate, what problem it solves, and
    how it improves maintainability, extensibility, testability, or
    separation of concerns.

Typical Usage:
    Explain how this module is normally used and how it fits into the
    overall application.
"""
```

For public classes, methods, and functions, use Google-style sections when
applicable:

```python
def example_function(value: str) -> bool:
    """Brief description of the function's purpose.

    Add additional explanation when needed to explain behavior or
    architectural intent.

    Args:
        value: Explain what the value represents.

    Returns:
        Explain what the returned value means.

    Raises:
        ValueError: Explain when the exception is raised.

    Examples:
        >>> example_function("example")
        True
    """
```

Use these sections as appropriate:

- `Args:`
- `Returns:`
- `Raises:`
- `Attributes:`
- `Examples:`
- `Note:`

When a class participates in a design pattern, identify the pattern in the
class docstring when useful for understanding the architecture.

Document **why the code exists**, not merely what the code literally does.

Avoid redundant documentation such as:

```python
def get_name():
    """Get the name."""
```

Prefer documentation that explains meaning or purpose:

```python
def get_name() -> str:
    """Return the normalized applicant name used for permit matching."""
```

If a design pattern spans several modules, identify each module's role in that
pattern, such as:

- interface or protocol;
- abstract base class;
- concrete strategy;
- adapter;
- factory;
- repository;
- service;
- facade; or
- client.

Do not repeat the full design-pattern explanation in every method.

When modifying an existing file for documentation only:

- do not refactor the implementation;
- do not rename functions, classes, or variables;
- do not reorganize modules;
- do not alter program behavior; and
- update obsolete or inaccurate docstrings when necessary.

The documentation must be suitable for both an academic software project and
a professional codebase. Another developer should be able to understand:

1. what the module does;
2. where it belongs in the application;
3. what design pattern it uses;
4. why that design pattern was chosen;
5. how the module is normally used;
6. what its public API does;
7. what its inputs and outputs represent; and
8. what important exceptions, assumptions, side effects, or edge cases exist.

Before completing a Python documentation task, verify that:

- every affected module has the required module-level docstring;
- every affected public class, method, and function has an accurate docstring;
- design-pattern claims match the implementation;
- type hints and executable statements are unchanged for documentation-only
  work; and
- the existing test suite still passes, allowing only already-documented
  expected failures.
