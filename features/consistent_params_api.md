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
   - Change `TransformParams` so scalar values are no longer valid.
   - Update `TransformConfig.params` to require an object when present.
   - Keep the types broad enough to cover current named parameter shapes.

2. Tighten parser validation.
   - Reject any `params` value that is not a dictionary/object.
   - Update error messages to explain that `params` must be an object with named fields.
   - Remove scalar dispatch paths from transform application helpers.

3. Align transform invocation semantics.
   - Use keyword arguments for every transform call that reads from JSON.
   - Verify the parser does not need positional fallback for any existing transform.
   - Make sure score-level and phrase-level transforms follow the same rule.

4. Update composition examples.
   - Rewrite `microtonal_demo.json` to use `{ "semitones": ... }`.
   - Rewrite `fugue_subject_answer_demo.json` to use named fields for `transpose` and `delay`.
   - Search the remaining compositions for scalar params and convert them.

5. Update tests.
   - Replace tests that currently expect scalar params to pass.
   - Add tests that assert scalar params are rejected.
   - Add tests that confirm the named-parameter form still parses and executes.

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
