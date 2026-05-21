# Fix Generic Callable Params in Transforms

## Goal

We need a clean way to get rid of  params: Mapping[str, object] in the transform modules so that the params are typed and we don't have to sprawl validation in the definitions. The TransformSpec should validate the params or that's its responsibility. Depending on when that happens, ideally the TransformSpec should validate params before we call the definition in the transform module.

## Problem

Transform functions currently use `Mapping[str, object]` for their params parameter, which requires repeated `isinstance` checks inside every transform for `rate`, `factor`, `dimension`, `max_deviation`, etc. This is redundant because params are already validated at the boundary in `composition/transformer.py` via `descriptor.validate_params()` before the transform is invoked.

## Design

1. **Define typed params models** per transform (e.g., `DriftParams`, `InvertParams`, `ScaleParams`). Each model matches the shape of the corresponding `TransformParamsSpec`.

2. **Update transform signatures** to use the typed params model instead of `Mapping[str, object]`.

3. **Update `PhraseTransformDefinition` / `ScoreTransformDefinition`** (or introduce new generic variants) so the `transform` callable carries the typed params contract.

4. **In `composition/transformer.py`**, after `descriptor.validate_params(transform_params)`, cast the dict to the typed params model before calling `descriptor.transform(...)`.

## Benefits

- **Single validation point**: Runtime validation happens once at the boundary via `TransformParamsSpec`.
- **No redundant checks inside transforms**: Transforms can trust their params (no `isinstance` guards needed).
- **Type-safe signatures**: Each transform's signature documents exactly what params it expects.
- **Eliminates `Mapping[str, object]`**: All internal transform code works with concrete, typed params.

## Approach

### Option A: TypedDict (lightweight)

```python
from typing import TypedDict
from transforms.base import ToneDimension

class DriftParams(TypedDict):
    dimension: ToneDimension
    rate: float

def drift_phrase_transform(context: PhraseTransformContext, params: DriftParams) -> Phrase:
    ...
```

- Pro: Easy, no imports needed at call sites.
- Con: Python won't enforce at runtime; still need `TransformParamsSpec.validate` at boundary.

### Option B: Frozen dataclass (safer)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class DriftParams:
    dimension: ToneDimension
    rate: float

def drift_phrase_transform(context: PhraseTransformContext, params: DriftParams) -> Phrase:
    ...
```

- Pro: Enforced at construction time; can use `dataclasses.asdict` for existing dict params.
- Con: Slightly more ceremony at the boundary.

### Option C: Generic TransformDefinition[P]

Wrap the transform callable with a typed generic:

```python
from typing import Generic, TypeVar

P = TypeVar("P")

class PhraseTransformDefinition(Generic[P]):
    name: str
    params_spec: TransformParamsSpec
    transform: Callable[[PhraseTransformContext, P], Phrase]
```

Then the registry entry binds the type:

```python
PHRASE_TRANSFORMS = {
    "drift": PhraseTransformDefinition[DriftParams](
        name="drift",
        params_spec=DRIFT_PARAMS_SPEC,
        transform=drift_phrase_transform,
    ),
}
```

And in the preparation layer, after validation, construct the typed params:

```python
# In composition/transformer.py
drift_params = DriftParams(
    dimension=transform_params["dimension"],
    rate=float(transform_params["rate"]),
)
descriptor.transform(context, drift_params)
```

### Option D: Distributed builder with registry

Add a `params_builder` field to `TransformDefinition` so each transform file owns its own ceremony. This avoids a centralized factory while keeping the registry as the single source of truth.

**In `transforms/base.py`:**
```python
@dataclass(frozen=True)
class PhraseTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    transform: Callable[[PhraseTransformContext, Any], Phrase]
    params_builder: Callable[[dict[str, object]], object] | None = None
```

**In each transform file (e.g., `transforms/basic/drift.py`):**
```python
@dataclass(frozen=True)
class DriftParams:
    dimension: ToneDimension
    rate: float

def _build_drift_params(raw: dict[str, object]) -> DriftParams:
    return DriftParams(
        dimension=raw["dimension"],
        rate=float(raw["rate"]),
    )
```

**In `transforms/registry.py` (single list):**
```python
"drift": PhraseTransformDefinition(
    name="drift",
    params_spec=DRIFT_PARAMS_SPEC,
    transform=drift_phrase_transform,
    params_builder=_build_drift_params,  # lives with transform
),
```

**In `composition/transformer.py`:**
```python
typed_params = (
    descriptor.params_builder(transform_params) 
    if descriptor.params_builder 
    else transform_params
)
descriptor.transform(context, typed_params)
```

- Pro: Registry stays as ONE list in ONE place; each transform owns its params construction.
- Con: Still needs params_builder boilerplate per transform.

### Option E: Typed parsing in TransformParamsSpec (preferred)

Make `TransformParamsSpec` responsible for both validation and normalization. This keeps the transform spec as the single boundary object: raw user/config params go in, typed params come out.

```python
@dataclass(frozen=True)
class DriftParams:
    dimension: ToneDimension
    rate: float

DRIFT_PARAMS_SPEC = TransformParamsSpec[DriftParams](
    params_model=DriftParams,
    fields={
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            required=True,
        ),
        "rate": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
    },
)
```

Then transform functions can depend on typed params directly:

```python
def drift_phrase_transform(context: PhraseTransformContext, params: DriftParams) -> Phrase:
    drifted_tones = drift_transform(
        flatten_phrase_tones(context.phrase),
        dimension=params.dimension,
        rate=params.rate,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=drifted_tones)])
```

**Core design:**

- `ParamSchema[T]` should expose `parse(value: object, field_name: str) -> T`.
- Existing `validate(...) -> None` can remain as a compatibility wrapper around `parse(...)`.
- `FloatParam.parse` returns `float`; `IntegerParam.parse` returns `int`; `BooleanParam.parse` returns `bool`; `StringParam.parse` returns `str`.
- Add `ToneDimensionParam.parse` returning `ToneDimension`.
- `EnumParam` can remain for string enum-like values such as intensity presets and return normalized `str`.
- `TransformParamsSpec[P].parse_params(raw_params) -> P` validates unknown/missing fields, parses each field, applies the custom validator if present, then constructs the frozen params dataclass.
- `PhraseTransformDefinition[P]` and `ScoreTransformDefinition[P]` should be generic and invoke transforms with `P`, not `Mapping[str, object]`.
- `PhraseTransformDefinition[P]` and `ScoreTransformDefinition[P]` should expose `transform(...)`, which accepts raw request params, parses them internally, and invokes the stored typed transform function.

**Why this is preferred:**

- It avoids `typing.cast` in normal application code.
- It avoids one-off `params_builder` boilerplate in every transform module.
- It removes redundant `isinstance` checks from transform functions without weakening runtime validation.
- It keeps validation, normalization, defaults, and typed construction in one place: the transform params spec.
- It makes the callable signature honest: transform functions receive the params type they actually require.

**Mypy implementation note:**

- The main typing risk is the heterogeneous transform registry: one registry maps names to transform definitions with different params types.
- Do not solve that by spreading `Any`, broad `Mapping[str, object]`, or `typing.cast` into transform modules.
- Keep any unavoidable type erasure localized to the registry/transformer boundary, where raw user params become typed params.
- Prefer `TransformParamsSpec[P].parse_params(...) -> P` and `PhraseTransformDefinition[P]` / `ScoreTransformDefinition[P]` methods that preserve the params type for each definition.
- If constructing a params dataclass generically with `params_model(**parsed_fields)` causes mypy friction, prefer a small typed factory on `TransformParamsSpec[P]` over distributed per-transform builders.
- The success condition is that transform modules receive concrete params objects and can pass mypy without local casts or defensive `isinstance` checks.

**Descriptor API decision:**

- The descriptor should expose a public `transform(...)` method, because callers are asking the descriptor to transform a phrase or score.
- That method should accept raw request params as `Mapping[str, object]`, parse them internally with `params_spec.parse_params(...)`, then call the typed transform function.
- Do not name this public method `parse_and_apply(...)`; parsing is an implementation detail and should not leak into the caller API.
- Do not name it `apply(...)`; `transform(...)` better matches the domain language already used by the project.
- Rename the stored callable field from `transform` to `transform_function` so the descriptor can expose a `transform(...)` method without a naming collision.
- Registry entries should therefore pass `transform_function=drift_phrase_transform` and callers should use `descriptor.transform(context, raw_params)` or `descriptor.transform(score, raw_params)`.

## Files to Change

- `transforms/base.py` — Make param schemas parse typed values; make `TransformParamsSpec`, `PhraseTransformDefinition`, and `ScoreTransformDefinition` generic.
- `transforms/basic/drift.py`, `inversion.py`, `scale.py` — Add typed params classes, update signatures.
- `transforms/complexity/*.py` — Same.
- `transforms/geological/*.py` — Same.
- `transforms/proportion/*.py` — Same.
- `transforms/basic/delay.py`, `repeat.py`, `reversal.py`, `transpose.py`, `pad_silence.py` — If they have params.
- `transforms/tempo/*.py` — Same.
- `transforms/counterpoint/*.py` — Same.
- `composition/transformer.py` — Invoke transforms through `descriptor.transform(...)` so validation/parsing stays hidden behind the descriptor.
- `tests/` — Update direct calls to use typed params.

## Status

- [ ] Removed all `isinstance(dimension, ...)` guards from transform functions (cleanup step 1).
- [ ] Add typed parsing to `TransformParamsSpec`.
- [ ] Define typed params models per transform.
- [ ] Update transform function signatures.
- [ ] Update registry definitions.
- [ ] Update `composition/transformer.py` boundary code.
- [ ] Update tests.
- [ ] Remove `parse_dimension` from `transforms/base.py` or keep only for external use.


## Final step

- check drift.py - it looks like there is a transform function not used in production code?
