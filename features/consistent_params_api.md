# Consistent `params` API

## Status

Proposed.

## Goal

Make composition JSON consistent so `params` is always an object with named fields. Remove support for scalar `params` values such as `1.0`, `7`, or `0.5`.

This is a breaking change, and compatibility is not a concern.

## Problem Statement

The current public API accepts both of these shapes:

```json
{ "name": "transpose", "params": 1.0 }
```

```json
{ "name": "drift", "params": { "dimension": "FREQUENCY", "rate": 0.1 } }
```

That means some transforms expose intent clearly, while others rely on an unnamed positional scalar. The JSON surface is inconsistent and makes the meaning of a number depend on the transform.

## Desired Shape

Every transform invocation should use object-shaped `params` with explicit names:

```json
{ "name": "transpose", "params": { "semitones": 1.0 } }
{ "name": "delay", "params": { "seconds": 1.8 } }
{ "name": "repeat", "params": { "count": 7 } }
{ "name": "score_scale", "params": { "dimension": "DURATION", "factor": 2.0 } }
```

If a transform truly has no parameters, it can keep omitting `params` entirely or use an empty object if that reads better in a specific case. The key point is that `params` should never be a raw number.

## Scope Of Change

Update the public JSON contract across the parser, schema, tests, and example compositions.

Transforms that currently accept scalar params include:

- `transpose` / `score_transpose`
- `delay` / `score_delay`
- `repeat` / `score_repeat`
- `accelerando`
- `ritardando`

Transforms that already use named parameters can remain object-shaped, but the implementation should verify that the parser no longer allows non-object params anywhere.

## Implementation Plan

1. Tighten the schema types.
   - 1.1. Inspect current `TransformParams` usage so the type change stays limited to the public composition JSON contract.
   - 1.2. Change `TransformParams` so scalar values are no longer valid.
   - 1.3. Keep `TransformParams` broad enough to cover current named parameter shapes, including nested profile configuration.
   - 1.4. Update `TransformConfig.params` to use the object-only `TransformParams` alias when present.
   - 1.5. Adjust only schema-adjacent annotations that now disagree with the object-only alias.
   - 1.6. Run the relevant tests or type checks to identify fallout.
   - 1.7. Defer runtime parser validation and dispatch changes to step 2.

2. Tighten parser validation.
   - 2.1. Inspect the current parser paths that read `params` from phrase and score transform specs.
   - 2.2. Update `_validate_transform_params` to reject any present `params` value that is not a dictionary/object.
   - 2.3. Update parser error messages to explain that `params` must be an object with named fields.
   - 2.4. Remove scalar dispatch paths from phrase-level transform application helpers.
   - 2.5. Remove scalar dispatch paths from score-level transform application helpers.
   - 2.6. Remove scalar dispatch paths from all-voices score transform application helpers.
   - 2.7. Verify relative phrase transforms and score target motif transforms still use keyword arguments only.
   - 2.8. Run the parser-focused tests to identify behavior that still depends on scalar params.
   - 2.9. Revisit the parser helper layer after the dispatch behavior is stable and simplify or inline any helpers that no longer earn their keep.

3. Align transform invocation semantics.
   - 3.1. Identify transforms whose Python function signatures currently rely on positional scalar arguments from JSON.
   - 3.2. Confirm each affected transform has an appropriate keyword parameter name for the new JSON object shape.
   - 3.3. Update transform signatures only where the existing parameter name does not match the desired public JSON name.
   - 3.4. Verify phrase-level transforms are invoked with keyword arguments from object-shaped `params`.
   - 3.5. Verify score-level transforms are invoked with keyword arguments from object-shaped `params`.
   - 3.6. Verify score-all-voices transforms are invoked with keyword arguments from object-shaped `params`.
   - 3.7. Search for remaining positional transform calls that originate from parsed JSON params.
   - 3.8. Run targeted tests for the affected transforms to confirm behavior is unchanged apart from the JSON API shape.

4. Update composition examples.
   - 4.1. Search all files in `compositions/` for scalar `params` values.
   - 4.2. Rewrite `microtonal_demo.json` to use `{ "semitones": ... }` for `transpose`.
   - 4.3. Rewrite `fugue_subject_answer_demo.json` to use named fields for `transpose` and `delay`.
   - 4.4. Convert any remaining phrase-level scalar params in `compositions/` to named parameter objects.
   - 4.5. Convert any remaining score-level scalar params in `compositions/` to named parameter objects.
   - 4.6. Re-run the scalar `params` search to confirm no composition examples still use raw numeric params.
   - 4.7. Parse or run the updated example compositions that previously used scalar params.

5. Update tests.
   - 5.1. Search the test suite for scalar `params` values.
   - 5.2. Identify tests that currently expect scalar phrase transform params to pass.
   - 5.3. Identify tests that currently expect scalar score transform params to pass.
   - 5.4. Replace scalar success cases with named-parameter object success cases.
   - 5.5. Add parser validation tests that assert scalar phrase transform params are rejected.
   - 5.6. Add parser validation tests that assert scalar score transform params are rejected.
   - 5.7. Add or update transform execution tests that confirm named-parameter forms still produce the expected musical output.
   - 5.8. Update expected error messages in tests to match the new object-only `params` validation.
   - 5.9. Run the full test suite and address failures caused by the API shape change.

6. Review documentation.
   - Update README examples.
   - Update feature docs that still show scalar params if they are meant to describe public JSON usage.

## Suggested Naming

Use parameter names that describe the musical quantity rather than the implementation detail:

- `transpose` -> `semitones`
- `delay` -> `seconds`
- `repeat` -> `count`
- `accelerando` -> `strength`
- `ritardando` -> `strength`

For transforms with multiple parameters, keep all fields explicit and self-describing.

## Parser-Level Error Shape

The parser should fail early with a direct message such as:

```text
Phrase transform params must be an object with named fields.
```

The message should point the user toward the new JSON contract instead of describing the old scalar behavior.

## Order Of Work

1. Change schema and parser validation.
2. Update tests for rejection and success cases.
3. Convert example compositions.
4. Update docs and any remaining references.

## Open Design Checks

- Whether any transforms should rename their parameter keys during the cleanup.
- Whether `params: {}` should be allowed for transforms that take no arguments, or whether omitting `params` entirely should remain the preferred form.
- Whether any docs should preserve the old examples for historical context, or whether they should be fully rewritten to the new API.
