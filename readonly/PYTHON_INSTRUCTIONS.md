# Instructions for using Python to code

## Type Safety and Casting

- Avoid `typing.cast` wherever possible. If you encounter a situation where mypy cannot infer a type from a registry or factory, refactor the registry to use **Generics** or encapsulate the behavior within a **Strategy** class that defines a consistent interface.

## Testing

You are operating in a sandboxed environment with a python virtual environment. The pytest command is located at `.venv/bin/pytest`. Use that executable to run the tests.

When working on Python tests:

1. Use Serena to inspect the changed symbols and find references.
2. Run targeted tests first:
   .venv/bin/pytest path/to/test_file.py -q
3. Run coverage for the touched module:
   .venv/bin/pytest --cov=package.module --cov-report=term-missing -q
4. Use uncovered lines from the coverage output to decide what tests to add.
5. Use Serena to modify source or tests at the symbol level when possible.
6. Re-run the targeted tests and coverage.
7. Only after green targeted tests, run the broader suite.
