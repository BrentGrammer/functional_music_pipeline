# True `params_spec`

## Goal

Make `TransformParamsSpec` describe the full public `params` surface for each transform, not just the subset of required field names.

## Problem

The current `params_spec` name implies a full schema, but the implementation only records `required_fields`. That leaves key API questions undocumented in code:

- which params are allowed
- which params are optional
- what types each param accepts
- whether extra fields are allowed
- whether any params are conditionally required

## Desired Shape

Each transform descriptor should declare a real spec for all supported params. At minimum, the spec should be able to answer:

- field name
- required or optional
- expected type or value kind
- whether unknown fields are allowed

Conditional rules such as `add_pedal_point.mode == "repeat"` requiring `pulse_duration` should also have a clear home, even if they remain custom validators at first.

## Implementation Plan

1. Define the target shape for `TransformParamsSpec`.
   - Add field-level metadata instead of only `required_fields`.
   - Decide whether the spec is just structural metadata or also drives runtime validation.

2. Introduce a field model.
   - Add something like `TransformParamFieldSpec`.
   - Record name, required flag, and expected kind/type.

3. Support transform-level rules.
   - Add a place for whole-object validation such as unknown-field handling and conditional requirements.
   - Keep this minimal at first.

4. Migrate descriptors incrementally.
   - Start with a few simple transforms like `transpose`, `delay`, and `repeat`.
   - Then migrate multi-field transforms like `scale`, `drift`, and `geological`.

5. Update parser validation to use the richer spec.
   - Validate missing required fields.
   - Reject unknown fields if that becomes part of the contract.
   - Add basic type validation where the metadata is clear enough.

6. Add descriptor-driven tests.
   - Verify required and optional fields from the descriptor metadata.
   - Avoid brittle error-text assertions.

7. Revisit conditional cases.
   - Decide whether cases like `pulse_duration` should stay as custom runtime checks or move into spec-driven validation.

## Notes

- This is the point where a schema library such as Pydantic may become worth evaluating.
- If we do not want to go this far, we should rename `params_spec` to reflect that it only tracks required fields.
