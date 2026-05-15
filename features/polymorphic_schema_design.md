# Polymorphic Parameter Schema Design

## Motivation

Currently, transform parameter specifications use a mix of an Enum (`TransformParamType`) and various fields on the `TransformParamFieldSpec` dataclass (like `allowed_enum_values`) to define validation rules. This becomes problematic when a parameter is a complex object (like a `StochasticProfile` dict) that has its own nested fields and validation requirements.

Instead of extending the `TransformParamFieldSpec` with mutually exclusive properties (e.g., having both `param_type` and `schema` fields, or hardcoding `is_object` checks), we can collapse the concepts of "Type" and "Shape" into a single, polymorphic `ParamSchema` base class.

## The Design

### 1. Polymorphic Schema Classes

We replace `TransformParamType` with a class hierarchy. Each subclass knows exactly how to validate its specific type of data.

```python
from dataclasses import dataclass, field
from typing import Mapping

class ParamSchema:
    """Base class for all parameter shapes/types."""
    def validate(self, value: object, field_name: str) -> None:
        raise NotImplementedError

@dataclass(frozen=True)
class FloatParam(ParamSchema):
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise ValueError(f"Param '{field_name}' must be a float.")

@dataclass(frozen=True)
class StringParam(ParamSchema):
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, str):
            raise ValueError(f"Param '{field_name}' must be a string.")

@dataclass(frozen=True)
class EnumParam(ParamSchema):
    allowed_values: tuple[str, ...]
    
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, str) or value.lower() not in (v.lower() for v in self.allowed_values):
            raise ValueError(f"Param '{field_name}' must be one of {self.allowed_values}.")

@dataclass(frozen=True)
class ObjectParam(ParamSchema):
    """Replaces the old 'OBJECT' type and provides nested validation."""
    fields: dict[str, "TransformParamFieldSpec"]
    
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, dict):
            raise ValueError(f"Param '{field_name}' must be an object/dictionary.")
        
        # Recursive validation of the nested fields happens here.
```

### 2. Streamlined Field Spec

The `TransformParamFieldSpec` no longer needs to manage `param_type`, enums, or other specific validation details. It only tracks whether the field is required and delegates validation to the schema.

```python
@dataclass(frozen=True)
class TransformParamFieldSpec:
    schema: ParamSchema | tuple[ParamSchema, ...] # Supports Unions
    required: bool = False
```

### 3. Declarative Transform Specs

Defining a transform spec becomes a clean, declarative definition of the exact shape expected, no matter how deeply nested.

```python
GEOLOGICAL_SPEC = TransformParamsSpec(
    fields={
        "profile": TransformParamFieldSpec(
            required=True,
            schema=ObjectParam(
                fields={
                    "type": TransformParamFieldSpec(required=True, schema=StringParam()),
                    "seed": TransformParamFieldSpec(schema=FloatParam()),
                    "volatility": TransformParamFieldSpec(schema=FloatParam()),
                }
            )
        ),
        "depth": TransformParamFieldSpec(schema=FloatParam()),
    }
)
```

## Benefits

1. **True Polymorphism:** The parser's validation logic no longer needs complex `switch` or `match` statements based on an Enum type. It simply calls `schema.validate(value, field_name)`.
2. **Infinite Nesting:** An `ObjectParam` can cleanly contain other `ObjectParam`s, allowing for fully recursive validation without special-case logic in the parser.
3. **Single Source of Truth:** We avoid structural conflicts in the dataclasses (e.g., avoiding cases where a developer sets `param_type=FLOAT` but also tries to define nested `fields`).
4. **Separation of Concerns:** The parser strictly validates the data shape. The individual transform functions remain responsible for taking that validated dictionary and instantiating domain objects (like `StochasticProfile`) as needed.

## Implementation Plan

Here is a step-by-step implementation plan designed to introduce the Polymorphic Schema approach incrementally. By introducing the new system alongside the old one, we ensure the tests keep passing at every single step.

### Step 1: Lay the Foundation (Additive Change)
*   **Action:** In `transforms/base.py`, define the new `ParamSchema` base class and the simple primitive subclasses (`FloatParam`, `IntegerParam`, `StringParam`, `BooleanParam`, `EnumParam`).
*   **Action:** Update `TransformParamFieldSpec` to include a new `schema: ParamSchema | None = None` field, keeping the old `param_type` and `allowed_enum_values` for now.

### Step 2: Bridge the Validation Logic
*   **Action:** Update `TransformDescriptor.validate_params` (and its helper methods) to first check if a `schema` is present on the field spec.
*   **Action:** If `schema` is present, use `schema.validate(field_value, field_name)`. If it is *not* present, fall back to the existing `_is_valid_transform_param_type` enum-based logic.

### Step 3: Incremental Migration of Primitive Transforms
*   **Action:** Go through the simple transforms one by one (e.g., `duration.py`, `transpose.py`, `delay.py`) and update their `TransformParamsSpec` to use the new `schema` field instead of `param_type`.
*   **Validation:** Run tests after migrating each batch of transforms to ensure the new primitive validators work exactly as the old enum validators did.

### Step 4: Implement Object Schema and Migrate Complex Transforms
*   **Action:** Implement the `ObjectParam` schema class in `transforms/base.py` with recursive validation logic.
*   **Action:** Migrate the complex transforms (like `geological.py` and `erosion.py`) that use the `"profile"` parameter to use the new `ObjectParam` schema.

### Step 5: Clean Up the Old System (Destructive Change)
*   **Action:** Now that all transforms use the `schema` field, remove `TransformParamType`, `allowed_enum_values`, and the legacy fallback logic (`_is_valid_transform_param_field`, `_is_valid_transform_param_type`) from `transforms/base.py`.
*   **Action:** Make the `schema` parameter on `TransformParamFieldSpec` strictly required instead of optional.

### Step 6: Flatten Stochastic Profiles into Top-Level Transforms
*   **Action:** Abandon the generic `geological` transform grouping entirely.
*   **Action:** Create new, distinct top-level transforms for every stochastic profile (e.g., `weierstrass`, `terraced_drift`, `cellular_automata`, `ridged_drop`, `random_drop`).
*   **Action:** In `transforms/registry.py`, define explicit, strict schemas for each of these new transforms. They will no longer use the `ObjectParam` escape hatch; instead, they will define their specific parameters (like `seed`, `step_size`, or `octaves`) directly at the top level of their `TransformParamsSpec`.

### Step 7: Refactor Transform Applicators
*   **Action:** Update the transformation logic (currently `apply_geological_transform`) to become a generic applicator (e.g., `apply_stochastic_profile`) that accepts any object fulfilling the `StochasticProfile` protocol.
*   **Action:** Write the individual transform functions (e.g., `apply_weierstrass_transform`) so they accept their specific, validated scalar arguments, instantiate their specific profile class, and call the generic applicator.

### Step 8: Complete the Abstraction and Clean Up
*   **Action:** Delete the obsolete `geological` and `score_geological` transforms from the registry.
*   **Action:** Delete `composition/profile_factory.py` entirely, as the registry-within-a-registry is no longer needed.
*   **Action:** Delete `resolve_profile_in_params` from `composition/parser.py`.
*   **Action:** Update the test suite to use the new top-level transform names instead of the old nested `geological` syntax.

### Step 9: Colocate Schemas with Implementations (DRY Refactor)
*   **Action:** To remove the duplication between the internal Python arguments and the external validation schema, move the `TransformParamsSpec` definitions out of the monolithic `transforms/registry.py` file.
*   **Action:** Define each schema directly inside the implementation file next to its corresponding wrapper function (e.g., `WEIERSTRASS_SPEC` in `transforms/geological.py`).
*   **Action:** Update `transforms/registry.py` to simply import the implementation function and its colocated spec, assembling the final registry without defining the schemas inline.

## Current Status Checkpoint

### Where We Are

We have cleanly completed **Step 8**.

The old nested stochastic-transform path has been removed:

*   `geological` and `score_geological` have been removed from the active transform surface.
*   `composition/profile_factory.py` has been deleted.
*   `resolve_profile_in_params` has been deleted from `composition/parser.py`.
*   The tests and example composition have been migrated to the flat top-level stochastic transform names.

### Step-by-Step Status

*   **Step 1:** Complete.
    *   The `ParamSchema` hierarchy exists in `transforms/base.py`.
*   **Step 2:** Effectively superseded by later cleanup.
    *   We no longer have a meaningful "bridge" phase because the legacy enum path has already been removed.
*   **Step 3:** Complete.
    *   Primitive transforms are using `schema=...` specs.
*   **Step 4:** Historically completed during the migration, but no longer part of the active design.
    *   `ObjectParam` was introduced to support nested object validation during the transition period.
    *   After the stochastic-transform flattening removed the nested profile path, `ObjectParam` became dead code and was deleted during cleanup.
*   **Step 5:** Functionally complete in the runtime path.
    *   `TransformParamType` and the old fallback-based validation path are gone from active use.
    *   `TransformParamFieldSpec.schema` is now required.
*   **Step 6:** Complete.
    *   The stochastic profiles have been flattened into top-level transforms such as `weierstrass`, `terraced_drift`, `cellular_automata`, `ridged_drop`, and `random_drop`.
*   **Step 7:** Complete.
    *   The generic applicator is now `apply_stochastic_profile`, and the profile-specific wrappers construct concrete profile instances and delegate to it.
*   **Step 8:** Complete.
    *   The abstraction cleanup and migration away from the old geological/profile-factory path is done.
*   **Step 9A:** Complete.
    *   `ObjectParam` has been removed as dead code.
*   **Step 9B:** Not started.
    *   Schemas are still centralized in `transforms/registry.py`.

## What Is Left

The feature is not blocked anymore. What remains is schema colocation and final verification after the successful Step 8 migration and Step 9A cleanup.

### Remaining Work in Order

#### Step 9B: Colocate Schemas with Implementations

With the `ObjectParam` cleanup complete, perform the DRY refactor originally planned as Step 9:

*   Move each `TransformParamsSpec` definition out of `transforms/registry.py`.
*   Define each schema next to its implementation function in the corresponding transform module.
*   Reduce `transforms/registry.py` to assembly only: import the transform function and its colocated spec, then register them.

Recommended rollout order:

1. Start with the flat stochastic transforms in `transforms/geological.py`.
2. Then migrate the small/simple transforms such as `delay`, `transpose`, `repeat`, and `pad_silence`.
3. Then migrate the more specialized transforms such as `stretto`, `add_pedal_point`, `accelerando`, and `ritardando`.

#### Step 9C: Final Verification Pass

After Step 9B:

*   Run the full test suite in the proper project environment.
*   Run `ruff`.
*   Run `mypy`.
*   Do a final pass over docs and examples to make sure they still match the active transform surface.

## Recommended Next Move

The next concrete action should be:

1. Perform Step 9B schema colocation.
2. Then do a final verification and documentation sweep.


### Final Cleanup

- Figure out if we need to use _interpolate_multiplier_at_position or can get rid of it (currently not referenced, does it need to be?)
