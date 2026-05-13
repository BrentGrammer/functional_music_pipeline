# Mypy Type Smell Analysis & Resolution Plan

## Overview

The recent migration to a descriptor-driven transform system has introduced a significant number of Mypy errors (123 errors currently). These errors indicate a "smell" where our transition from static type hints to dynamic runtime descriptors has left the type system unable to verify the safety of our code.

## Error Categories & Root Causes

### 1. The "None Unpacking" Smell
**Symptom:** Mypy complains `Argument after ** must be a mapping, not "dict[str, object] | None"` in `composition/parser.py`.
**Root Cause:** The function `resolve_profile_in_params` accepts `dict | None` and returns `dict | None`. When we pass a `dict` into it, Mypy doesn't know that we are guaranteed to get a `dict` back. Using `assert x is not None` in production code just to satisfy a linter is an anti-pattern.
**Resolution:**
- Use `@overload` from the `typing` module to explicitly define the input/output relationships.
- `(dict) -> dict` and `(None) -> None`.
- This tells Mypy exactly what to expect, allowing us to remove all the `assert` and `cast` hacks around parameter unpacking.

### 2. The "Callable Opaque" Smell
**Symptom:** Mypy complains `Returning Any from function declared to return "Score"` (or `list[Tone]`).
**Root Cause:** In `transforms/base.py`, the `TransformDescriptor` defines its `transform` field simply as a generic `Callable`. To Mypy, `Callable` means "a function that takes anything and returns `Any`." When the parser executes `descriptor.transform(...)`, Mypy loses all type safety and assumes the result is `Any`.
**Resolution:**
- Make `TransformDescriptor` a **Generic** class (`TransformDescriptor[T_Transform]`).
- Define specific `Protocol` types for our different transform signatures (e.g., `PhraseTransformProtocol`, `ScoreTransformProtocol`).
- This allows Mypy to know exactly what kind of function is inside the descriptor and, crucially, exactly what it returns.

### 3. The "TypedDict Variance" Smell (The Bulk of the Test Errors)
**Symptom:** Dozens of errors in tests like `Argument 1 to "parse_composition" has incompatible type "dict[str, object]"; expected "CompositionDocument"`.
**Root Cause:** `TypedDict` in Python is very strict (invariant). When defining a raw dictionary in a test (`json_data = {"motifs": ...}`), Mypy infers its type as a generic `dict[str, object]`. Passing that to `parse_composition(doc: CompositionDocument)` is rejected, even if the keys match perfectly, because a generic dict is not guaranteed to have the strict structure of the `TypedDict`. By removing the specific transform param types from `schema.py`, we widened the types so much that the "parent" structures can no longer be verified.
**Resolution:**
- In our tests, explicitly annotate the test data variables.
- Change `composition_document = {...}` to `composition_document: CompositionDocument = {...}`.
- This tells Mypy to evaluate the dictionary literal against the `CompositionDocument` schema immediately, fixing the variance issues without altering production code.

### 4. Minor Arithmetic / Return Smells
**Symptom:** Errors like `Returning Any from function declared to return "float"` in `golden_ratio.py` and `duration.py`, or `Returning Any` in `tone.py` (NumPy related).
**Root Cause:** Sometimes Python's `sum()` or division operations on dynamic types result in Mypy inferring `Any`.
**Resolution:**
- Small, targeted fixes. E.g., explicitly casting the result of `sum()` to `float()`, or ensuring our type hints for NumPy arrays are correct.

## Proposed Iterative Implementation Plan

To keep the steps small and manageable, we will tackle the smells in the following order:

1. **Overloads:** Fix `resolve_profile_in_params` with `@overload` and remove the `assert` statements.
2. **Generics & Protocols:** Make `TransformDescriptor` generic and strictly type the transform callables.
3. **Test Annotations:** Go through the test suite and properly annotate the raw dictionaries as `CompositionDocument`, `PhraseConfig`, etc.
4. **Minor Arithmetic:** Clean up the isolated return type errors in the transform math and tone definitions.

## Engineering Standards

- **No `cast` unless strictly necessary:** `cast` is a sign that the design is fighting the type system.
- **No `assert` for type narrowing in production:** Use explicit error handling, overloads, or better type definitions.
- **Prefer Protocols over Callables:** Protocols provide named, structural contracts that Mypy can actually verify.
- **Variance Awareness:** Be explicit about whether a dictionary is a "closed" model (`TypedDict`) or an "open" bag of values (`Mapping`).
