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

## Current Decision

Continue using transform descriptors and upgrade `TransformParamsSpec` into a true spec. Do not introduce Pydantic at this stage.

## Rationale

The current architecture is already descriptor-driven:

- `TransformParamsSpec` exists, but currently only records required field names.
- parser validation only checks that `params` is an object and that required fields are present.
- transforms are still plain Python functions invoked with `**transform_params`.

That means the missing piece is truthful descriptor metadata, not a new modeling framework.

Pydantic is not the right next step yet for these reasons:

- it would add a second abstraction layer around a still-simple function-call based transform system
- it would likely require either one model per transform or a more complex discriminated-union structure
- some params, such as `profile`, already cross a boundary from input config into runtime objects, which is easier to keep explicit in a custom spec system
- the current parameter surface is still mostly small and flat, with only a few conditional cases

Pydantic may become worth revisiting later if the composition document becomes much more nested, if we want generated JSON schema, or if transform params evolve into richer domain models instead of lightweight keyword argument objects.

## Recommended Spec Shape

Add richer field-level metadata to `TransformParamsSpec` rather than only `required_fields`.

Suggested direction:

- add a `TransformParamFieldSpec`
- record field name
- record whether the field is required or optional
- record the expected type or value kind
- optionally record default values or allowed values for enum-like fields
- add a transform-level policy for whether unknown fields are allowed
- add an optional transform-level validator hook for conditional rules

Conditional requirements should stay minimal at first. For example, `add_pedal_point` can continue using a dedicated validator rule for `mode == "repeat"` requiring `pulse_duration` before deciding whether to generalize that pattern further.

## Implementation Plan

1. Define the target shape for `TransformParamsSpec`.
   - Add field-level metadata instead of only `required_fields`.
   - Keep the design lightweight and descriptor-driven.
   - Use the spec for runtime validation, not just documentation metadata.

2. Introduce a field model.
   - Add something like `TransformParamFieldSpec`.
   - Record field name, required flag, and expected kind/type.
   - Keep the first supported kinds small and explicit: `number`, `integer`, `string`, `boolean`, `enum`, and `object`.
   - Allow room for nested object specs where a param itself has internal structure.

3. Support transform-level rules.
   - Add a place for whole-object validation such as unknown-field handling and conditional requirements.
   - Add an optional validator hook for cross-field and conditionally required rules.
   - Keep this minimal at first rather than trying to encode every rule in the field model.

4. Upgrade parser validation to be spec-driven.
   - Replace the current validation that only checks for an object and required field presence.
   - Validate missing required fields.
   - Validate allowed vs unknown fields.
   - Validate basic value kinds where the metadata is clear enough.
   - Do not add coercion. Keep input validation explicit and strict.

5. Preserve the current transform execution model.
   - Keep transforms as plain Python functions invoked with `**transform_params`.
   - Do not introduce a second execution abstraction or a model-per-transform runtime layer.
   - Limit this work to truthful descriptor metadata plus parser validation.

6. Migrate descriptors incrementally, starting with the simplest flat transforms.
   - Start with `transpose`, `delay`, and `repeat`.
   - These provide the smallest surface area for validating the new field model and parser behavior.
   - Add descriptor-driven tests for these transforms before moving to more complex cases.

7. Migrate the common multi-field flat transforms.
   - Continue with `scale`, `drift`, `pad_silence`, `accelerando`, and `ritardando`.
   - Make enum-like fields explicit in the metadata, such as `dimension` and `position`.
   - Make optional fields explicit rather than leaving them as implicit kwargs.

8. Keep `geological` as a nested spec rather than flattening it into separate top-level transforms.
   - The nested `profile` object is a legitimate domain sub-object, not an API smell.
   - Keep `geological` as the canonical transform shape with outer fields like `profile`, `dimension`, and `max_deviation`.
   - Add nested spec support so `profile` can declare its own shape such as `type` and `params`.
   - If user ergonomics later justify flatter aliases like `weierstrass`, those should be convenience aliases rather than the primary model.

9. Use transform-level custom validators for conditional cases.
   - Keep conditional rules like `add_pedal_point.mode == "repeat"` requiring `pulse_duration` in dedicated validator hooks first.
   - Use the same mechanism for cross-field constraints and profile-specific geological validation.
   - Revisit later whether any of these rules should move deeper into the spec model.

10. Add descriptor-driven tests for contract behavior.
   - Verify required and optional fields from the descriptor metadata.
   - Verify wrong basic types are rejected.
   - Verify unknown fields are rejected when the descriptor disallows them.
   - Verify custom conditional validator rules fail correctly.
   - Avoid brittle error-text assertions.

11. Reassess after the first full migration slice.
   - After migrating simple flat transforms, one conditional transform, and `geological`, evaluate whether the custom spec still feels clean and proportionate.
   - Only revisit a schema library such as Pydantic if the transform params or composition document become substantially more nested or model-heavy.

12. Use renaming as a fallback only.
   - If this work is not completed, rename `params_spec` so it no longer implies a full schema.
   - This is the fallback path, not the recommended direction.

## Notes

- A schema library such as Pydantic may become worth evaluating later, but it is not the current recommendation.
- If we do not want to go this far, we should rename `params_spec` to reflect that it only tracks required fields.
