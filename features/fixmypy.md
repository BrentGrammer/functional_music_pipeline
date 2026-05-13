# Mypy Type Smell Analysis & Resolution Plan

## Overview

The recent migration to a descriptor-driven transform system has introduced a significant number of Mypy errors. These errors are not just noise; they indicate a "smell" where our transition from static type hints to dynamic runtime descriptors has left the type system unable to verify the safety of our code.

## Error Categories

### 1. The "Callable Opaque" Smell
**Problem:** `TransformDescriptor.transform` is typed as a generic `Callable`. Mypy treats the return value of any generic `Callable` as `Any`.
**Location:** `composition/parser.py` (e.g., `Returning Any from function declared to return "Score"`)
**The Smell:** We are losing type safety at the exact moment of execution. The parser "knows" what the transform should return based on its scope, but Mypy cannot see that link.
**Resolution:**
- Replace the generic `Callable` in `TransformDescriptor` with specific `Protocol` types or specialized generic types.
- Define `PhraseTransform(Protocol)`, `ScoreTransform(Protocol)`, etc.
- Update `TransformDescriptor` to use these protocols so Mypy knows that a `PHRASE` scope transform returns `list[Tone]` and a `SCORE` scope transform returns `Score`.

### 2. The "None Unpacking" Smell
**Problem:** `resolve_profile_in_params` returns `dict[str, object] | None`, but it is being unpacked with `**` in contexts where we expect a dictionary.
**Location:** `composition/parser.py` (e.g., `Argument after ** must be a mapping, not "dict[str, object] | None"`)
**The Smell:** Using `assert x is not None` in production code to satisfy a linter is an anti-pattern. If the type system says it could be `None`, we must handle that case explicitly or refine the type.
**Resolution:**
- Refine the signature of `resolve_profile_in_params`. If it receives a `dict`, it should return a `dict`.
- Use `@overload` to tell Mypy: `(dict) -> dict` and `(None) -> None`.
- This removes the need for `assert` or `cast` at the call site.

### 3. The "TypedDict Variance" Smell
**Problem:** Functions like `parse_composition` expect a `CompositionDocument` (a `TypedDict`), but are being passed a plain `dict[str, object]`.
**Location:** `tests/test_json_parser.py` and other test files.
**The Smell:** `TypedDict` is "invariant." A plain `dict` is not a `CompositionDocument` according to Mypy, even if the keys match. By removing the specific transform param types from `schema.py`, we widened the types so much that the "parent" structures can no longer be verified.
**Resolution:**
- Use `Mapping[str, Any]` or `ReadOnlyDict` patterns where possible to allow covariance.
- In tests, explicitly annotate dictionaries: `doc: CompositionDocument = { ... }`.
- Re-introduce high-level "shape" types in `schema.py` if they provide value for static analysis without duplicating the detailed field validation now handled by descriptors.

## Engineering Standards

- **No `cast` unless strictly necessary:** `cast` is a sign that the design is fighting the type system.
- **No `assert` for type narrowing in production:** Use explicit error handling or better type definitions.
- **Prefer Protocols over Callables:** Protocols provide named, structural contracts that Mypy can actually verify.
- **Variance Awareness:** Be explicit about whether a dictionary is a "closed" model (`TypedDict`) or an "open" bag of values (`Mapping`).
