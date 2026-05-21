# Fix Generic Callable Params in Transforms

## Goal

Remove `Mapping[str, object]` from transform module function signatures and replace it with concrete typed params models. Runtime validation and parsing should happen once at the registered transform boundary, before the transform function is invoked.

## Problem

Transform functions currently receive raw params as `Mapping[str, object]`, which forces repeated defensive checks for fields like `rate`, `factor`, `dimension`, and `max_deviation`. This duplicates validation that already belongs at the transform boundary and makes the transform signatures less honest.

## Active Design

### Typed params models

- Define a frozen dataclass params model for each transform that takes params, such as `DriftParams`, `ScaleParams`, and `RepeatParams`.
- Use a shared frozen `NoParams` dataclass for transforms with no configurable params.
- Transform functions should receive those concrete params models directly.
- Transform functions should not contain local `isinstance` guards for already-validated params.

Example:

```python
@dataclass(frozen=True)
class DriftParams:
    dimension: ToneDimension
    rate: float


def drift_phrase_transform(context: PhraseTransformContext, params: DriftParams) -> Phrase:
    drifted_tones = drift_transform(
        flatten_phrase_tones(context.phrase),
        dimension=params.dimension,
        rate=params.rate,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=drifted_tones)])
```

### Typed param parsing

- Make `ParamSchema[T]` expose `parse(value: object, field_name: str) -> T`.
- Keep `validate(...) -> None` only as a compatibility wrapper around `parse(...)` if still needed.
- `FloatParam.parse` returns `float`; `IntegerParam.parse` returns `int`; `BooleanParam.parse` returns `bool`; `StringParam.parse` returns `str`.
- Keep `parse_dimension(...)` for external/raw-input boundary parsing in `composition/parser.py`.
- Add `ToneDimensionParam.parse` returning `ToneDimension`; it should reuse `parse_dimension(...)` so parser and transform param parsing share the same dimension normalization behavior.
- Keep `EnumParam` for string enum-like values such as intensity presets; it should return normalized `str`.
- Add a `default` field to `TransformParamFieldSpec` so optional/defaulted params are defined in the spec instead of transform functions calling `params.get(...)`.
- Make `TransformParamsSpec[P]` use a typed factory, such as `params_factory: Callable[[Mapping[str, object]], P]`, to construct params models after field parsing.
- Do not use generic dataclass construction with `params_model(**parsed_fields)` as the primary design; the typed factory is the official mypy-friendly construction path.
- Do not add distributed per-transform builders outside the params spec.
- Make `TransformParamsSpec[P].parse_params(raw_params) -> P` validate unknown/missing fields, parse raw field values, apply defaults, construct the typed params model, then run the custom validator if present.
- Field schemas validate and parse raw values. Custom validators should run on typed params as `Callable[[P], None]` so cross-field validation can use concrete attributes without defensive type checks.

### Transform definitions

- Make `PhraseTransformDefinition[P]` and `ScoreTransformDefinition[P]` generic.
- Rename the stored callable field from `transform` to `transform_function`.
- Add a public `transform(...)` method on each definition. This method accepts raw request params, parses them internally with `params_spec.parse_params(...)`, then calls `transform_function(...)` with typed params.
- Callers should use `descriptor.transform(context, raw_params)` or `descriptor.transform(score, raw_params)`.
- Do not expose `parse_and_apply(...)`; parsing is an implementation detail.
- Do not use `apply(...)`; `transform(...)` matches the project domain language.

Example:

```python
@dataclass(frozen=True)
class PhraseTransformDefinition(Generic[P]):
    name: str
    params_spec: TransformParamsSpec[P]
    transform_function: Callable[[PhraseTransformContext, P], Phrase]

    def transform(
        self,
        context: PhraseTransformContext,
        raw_params: Mapping[str, object],
    ) -> Phrase:
        params = self.params_spec.parse_params(raw_params)
        return self.transform_function(context, params)
```

### Registry typing

- Use Protocols named `RegisteredPhraseTransform` and `RegisteredScoreTransform` for registry values.
- The registered transform Protocols should expose only the registry-facing contract: `name` and `transform(...)`.
- Keep each concrete params type inside `PhraseTransformDefinition[P]` / `ScoreTransformDefinition[P]`.
- Registry annotations should be `dict[str, RegisteredPhraseTransform]` and `dict[str, RegisteredScoreTransform]`, not `dict[str, PhraseTransformDefinition[Any]]`.
- Do not spread `Any`, broad `Mapping[str, object]`, or `typing.cast` into transform modules.
- Do not name the registry-facing abstraction `AnyPhraseTransformDefinition` or similar; that names the typing compromise instead of the domain role.

Example:

```python
class RegisteredPhraseTransform(Protocol):
    name: str

    def transform(
        self,
        context: PhraseTransformContext,
        raw_params: Mapping[str, object],
    ) -> Phrase:
        ...


PHRASE_TRANSFORMS: dict[str, RegisteredPhraseTransform] = {
    "drift": PhraseTransformDefinition[DriftParams](
        name="drift",
        params_spec=DRIFT_PARAMS_SPEC,
        transform_function=drift_phrase_transform,
    ),
}
```

## Files to Change

- `transforms/base.py` — Add typed parsing, generic params specs, generic transform definitions, registered transform Protocols, and public definition `transform(...)` methods.
- Transform modules — Add params dataclasses, update transform function signatures, remove redundant param type guards.
- `transforms/registry.py` — Use `transform_function=...` and registered transform Protocol dict annotations.
- `composition/transformer.py` — Invoke transforms through `descriptor.transform(...)` so validation/parsing stays hidden behind the registered transform.
- `tests/` — Update direct transform calls to pass typed params models where they bypass the descriptor.

## Status

- [ ] Add typed parsing to `ParamSchema` and `TransformParamsSpec`.
- [ ] Add shared `NoParams`.
- [ ] Add defaults to `TransformParamFieldSpec`.
- [ ] Make custom validators operate on typed params.
- [ ] Add `RegisteredPhraseTransform` and `RegisteredScoreTransform` Protocols.
- [ ] Make `PhraseTransformDefinition` and `ScoreTransformDefinition` generic.
- [ ] Rename stored callable field to `transform_function`.
- [ ] Route production transform invocation through registered transform `transform(...)`.
- [ ] Define typed params models per transform.
- [ ] Update transform function signatures and remove redundant `isinstance` guards.
- [ ] Update registry definitions.
- [ ] Update tests.
- [ ] Keep `parse_dimension` for `composition/parser.py` and reuse it from `ToneDimensionParam`.
- [ ] Check `drift.py` for any transform function that is not used in production code.

## Success Criteria

- Transform modules receive concrete params objects, not `Mapping[str, object]`.
- Mypy passes without local casts or `Any` in transform modules.
- Runtime validation errors still happen at the registered transform/spec boundary.
- Existing transform behavior is preserved.
