# True `params_spec`

## Goal

Make `TransformParamsSpec` describe the full public `params` surface for each transform, not just the subset of required field names.

## Problem

The current `params_spec` name implies a full schema, but the implementation only records `required_fields`. That leaves key API questions undocumented in code:

- which params are allowed
- which params are optional
- what types each param accepts
- whether any params are conditionally required

## Desired Shape

Each transform descriptor should declare a real spec for all supported params. At minimum, the spec should be able to answer:

- field name
- required or optional
- expected parameter type

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
- record the expected parameter type
- allow the expected parameter type to be a simple union when a public param accepts more than one shape
- record allowed values for enum-like fields
- add an optional transform-level validator hook for conditional rules

Conditional requirements should stay minimal at first. For example, `add_pedal_point` can continue using a dedicated validator rule for `mode == "repeat"` requiring `pulse_duration` before deciding whether to generalize that pattern further.

The target shape should stay shallow. We do not want recursive nested specs or a mini schema engine. Top-level transform params should always be strict, and any nested object details should be handled by a dedicated validator for that transform.

Defaults should stay in transform function signatures for now. The spec should define the public JSON parameter shape, while transform functions remain the source of runtime default behavior. This avoids duplicating defaults across the descriptor metadata and the actual function signature.

Proposed end-state sketch:

```python
class TransformParamType(Enum):
    FLOAT = auto()
    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    ENUM = auto()
    OBJECT = auto()


@dataclass(frozen=True)
class TransformParamFieldSpec:
    param_type: TransformParamType | tuple[TransformParamType, ...]
    required: bool = False
    allowed_enum_values: tuple[object, ...] = ()


@dataclass(frozen=True)
class TransformParamsSpec:
    fields: dict[str, TransformParamFieldSpec] = field(default_factory=dict)
    validator: Callable[[dict[str, object]], None] | None = None
```

This sketch is intentionally concrete enough to clarify the direction, but it should not be treated as a locked final API until implementation work confirms that it fits the parser and descriptor usage cleanly.

The `tuple[TransformParamType, ...]` form is the recommended way to represent simple union params. Some public params intentionally accept either a named preset string or a continuous numeric value. The spec should describe that directly rather than adding transform-specific bypass flags or a second nested variant model.

Examples:

```python
TransformParamFieldSpec(
    param_type=TransformParamType.FLOAT,
    required=True,
)

TransformParamFieldSpec(
    param_type=(TransformParamType.ENUM, TransformParamType.FLOAT),
    required=True,
    allowed_enum_values=("none", "low", "medium", "high", "extreme"),
)
```

Keep `TransformParamType.FLOAT` as the descriptor for continuous numeric parameters. Do not rename it to a generic `NUMBER` type in this iteration. `FLOAT` communicates that these params may vary continuously, while `INTEGER` remains distinct for discrete count-like values. Parser validation may still accept JSON integer literals for `FLOAT` fields when that is semantically valid for a continuous parameter, but the spec should continue to express the intended domain as `FLOAT`.

This keeps the contract focused on:

- which top-level fields exist
- which ones are required
- what parameter type or simple union of types each field accepts
- what enum-like values are allowed
- what custom validation rules still apply

The split of responsibilities should be:

- transform function signatures own runtime defaults
- `TransformParamsSpec` owns public JSON param shape
- validator callables own cross-field, conditional, and nested-object rules

The stored representation should move to the final shape immediately:

- `TransformParamsSpec` should store only `fields`
- each field should carry its own `required` flag
- any temporary `required_fields` compatibility should be a derived property during migration rather than a second stored shape

Unknown top-level param fields should always be invalid. We do not need an `allow_unknown_fields` option in the public spec model.

## Validator Placement

Validator callables should live in a small dedicated validation module rather than inside the transform functions themselves.

Suggested direction:

- add a module such as `composition/transform_params_validation.py`
- define transform-specific validators there, such as `validate_add_pedal_point_params(...)`
- attach those validator callables from the transform descriptors

This keeps responsibilities cleaner:

- transform modules stay focused on musical transformation behavior
- field metadata handles simple top-level param shape checks
- validator callables handle cross-field rules, conditional requirements, and nested object validation
- parser-facing contract validation stays in one obvious place rather than being scattered across transform modules

If a validator needs deeper domain-specific checks, it can delegate to a helper such as the profile factory or a future specialized profile validation helper rather than reimplementing that logic inline.

## Implementation Plan

1. Define the target shape for `TransformParamsSpec`.
   - Add field-level metadata instead of only `required_fields`.
   - Keep the design lightweight and descriptor-driven.
   - Use the spec for runtime validation, not just documentation metadata.
   - Do not store runtime default values in the spec during this iteration.
   - Make `fields` the only stored representation in `TransformParamsSpec`.
   - If compatibility with older parser code is temporarily needed, expose `required_fields` only as a derived property from `fields`.

2. Introduce a field model.
   - Add something like `TransformParamFieldSpec`.
   - Record field name, required flag, and expected parameter type.
   - Allow `param_type` to be either a single `TransformParamType` or a tuple of `TransformParamType` values for simple union params.
   - Use a `TransformParamType` enum rather than raw strings for supported parameter types.
   - Keep the first supported parameter types small and explicit: `float`, `integer`, `string`, `boolean`, `enum`, and `object`.
   - Keep `float` as the continuous numeric type and `integer` as the discrete numeric type. Do not replace `float` with a broad `number` label.
   - Keep the model shallow rather than recursively describing nested object internals.
   - Do not support two constructor shapes for `TransformParamsSpec`; avoid a split between stored `required_fields` and stored `fields`.

3. Support transform-level rules.
   - Add an optional validator hook for cross-field rules, conditional requirements, and nested object validation.
   - Keep this minimal at first rather than trying to encode every rule in the field model.

4. Upgrade parser validation to be spec-driven.
   - Replace the current validation that only checks for an object and required field presence.
   - Validate missing required fields by reading the per-field `required` metadata.
   - Reject unknown top-level fields by default.
   - Validate basic parameter types, including tuple-based union types such as `(enum, float)`.
   - Treat `enum` plus `allowed_enum_values` as an allowed-value check for the enum branch of a union.
   - Do not add coercion. Keep input validation explicit and strict.

5. Preserve the current transform execution model.
   - Keep transforms as plain Python functions invoked with `**transform_params`.
   - Keep runtime defaults in transform function signatures so direct Python calls and parser-mediated calls behave consistently.
   - Do not introduce a second execution abstraction or a model-per-transform runtime layer.
   - Limit this work to truthful descriptor metadata plus parser validation.

6. Migrate descriptors incrementally, starting with the simplest flat transforms.
   - Start with `reverse`, `transpose`, `delay`, and `repeat`.
   - These provide the smallest surface area for validating the new field model and parser behavior across both no-param and required-param transforms.
   - Add descriptor-driven tests for these transforms before moving to more complex cases.

7. Migrate the common multi-field flat transforms.
   - Continue with `scale`, `drift`, `pad_silence`, `accelerando`, and `ritardando`.
   - Make enum-like fields explicit in the metadata, such as `dimension` and `position`.
   - Make optional fields explicit rather than leaving them as implicit kwargs.

8. Keep `geological` as a nested spec rather than flattening it into separate top-level transforms.
   - The nested `profile` object is a legitimate domain sub-object, not an API smell.
   - Keep `geological` as the canonical transform shape with outer fields like `profile`, `dimension`, and `max_deviation`.
   - Treat `profile` as a top-level field with parameter type `object`, then validate its internal shape with a dedicated validator.
   - If user ergonomics later justify flatter aliases like `weierstrass`, those should be convenience aliases rather than the primary model.

9. Use transform-level custom validators for conditional cases.
   - Keep conditional rules like `add_pedal_point.mode == "repeat"` requiring `pulse_duration` in dedicated validator hooks first.
   - Use the same mechanism for cross-field constraints and profile-specific geological validation.
   - Define those validator callables in a dedicated composition-side validation module rather than embedding them in transform modules.
   - Revisit later whether any of these rules should move deeper into the spec model.

10. Add descriptor-driven tests for contract behavior.
   - Verify required and optional fields from the descriptor metadata.
   - Verify wrong basic types are rejected.
   - Verify unknown top-level fields are always rejected.
   - Verify custom conditional validator rules fail correctly.
   - Avoid brittle error-text assertions.

11. Remove transitional compatibility once the descriptor migration is complete.
   - Remove any temporary compatibility property or bridging code kept only to support the old `required_fields` access pattern.
   - Leave `fields` as the only long-term source of truth inside `TransformParamsSpec`.

12. Collapse duplicate transform-param type definitions in `composition/schema.py`.
   - Keep `composition/schema.py` focused on coarse composition document structure rather than per-transform param contracts.
   - Remove or relax transform-param aliases such as `StandardTransformParams`, `GeologicalTransformParams`, and the `TransformParams` union once descriptor-driven validation is fully in place.
   - Let descriptor metadata and validator callables be the only source of truth for transform-specific param shape.
   - Keep any remaining schema typing broad enough to model “params is an object” without trying to restate per-transform contracts.

13. Reassess after the first full migration slice.
   - After migrating simple flat transforms, one conditional transform, and `geological`, evaluate whether the custom spec still feels clean and proportionate.
   - Only revisit a schema library such as Pydantic if the transform params or composition document become substantially more nested or model-heavy.

14. Use renaming as a fallback only.
   - If this work is not completed, rename `params_spec` so it no longer implies a full schema.
   - This is the fallback path, not the recommended direction.

## Notes

- A schema library such as Pydantic may become worth evaluating later, but it is not the current recommendation.
- If we do not want to go this far, we should rename `params_spec` to reflect that it only tracks required fields.
