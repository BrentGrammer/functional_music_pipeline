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
- Keep raw dimension string normalization in `composition/parser.py`, because that is the external user-input boundary.
- Transform param parsing should validate that dimension values are already `ToneDimension` instances. It should not parse raw dimension strings or duplicate parser normalization.
- Consider moving `parse_dimension(...)` out of `transforms/base.py` and into `composition/parser.py` or a parser-adjacent module so user-input normalization is not owned by the transform base layer.
- Keep `EnumParam` for string enum-like values such as intensity presets; it should return normalized `str`.
- Add a `default` field to `TransformParamFieldSpec` so optional/defaulted params are defined in the spec instead of transform functions calling `params.get(...)`.
- Make `TransformParamsSpec[P]` use a typed factory, such as `params_factory: Callable[[Mapping[str, object]], P]`, to construct params models after field parsing.
- Do not use generic dataclass construction with `params_model(**parsed_fields)` as the primary design; the typed factory is the official mypy-friendly construction path.
- Do not add distributed per-transform builders outside the params spec.
- Make `TransformParamsSpec[P].parse_params(raw_params) -> P` validate unknown/missing fields, parse raw field values, apply defaults, construct the typed params model, then run the custom validator if present.
- Field schemas validate and parse raw values. Custom validators should run on typed params as `Callable[[P], None]` so cross-field validation can use concrete attributes without defensive type checks.
- Keep `base.py` limited to generic transform-boundary parsing infrastructure. Do not let it become a dumping ground for per-transform rules; transform-specific validation belongs in that transform's `TransformParamsSpec`, and transform functions should still receive already-validated typed params.

### Transform definitions

- Make `PhraseTransformDefinition[P]` and `ScoreTransformDefinition[P]` generic.
- Rename the stored callable field from `transform` to `transform_function`.
- Add a public `transform(...)` method on each definition. This method accepts raw request params, parses them internally with `params_spec.parse_params(...)`, then calls `transform_function(...)` with typed params.
- Callers should use `registered_transform.transform(context, raw_params)` or `registered_transform.transform(score, raw_params)`.
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
- `composition/transformer.py` — Invoke transforms through `registered_transform.transform(...)` so validation/parsing stays hidden behind the registered transform.
- `tests/` — Update direct transform calls to pass typed params models where they bypass the registered transform.

## Staged Implementation Plan

### Stage 1: Base infrastructure

Recommended model: `GPT-5.4`.

- Update `transforms/base.py` with typed parsing primitives:
  - `ParamSchema[T].parse(...)`
  - shared frozen `NoParams`
  - `TransformParamFieldSpec.default`
  - generic `TransformParamsSpec[P]`
  - typed `params_factory`
  - typed custom validators as `Callable[[P], None]`
- Add a dimension param schema only if needed to validate already-normalized `ToneDimension` values; it must not accept raw strings.
- Add `RegisteredPhraseTransform` and `RegisteredScoreTransform` Protocols.
- Make `PhraseTransformDefinition[P]` and `ScoreTransformDefinition[P]` generic.
- Rename the stored callable field to `transform_function`.
- Add public definition `transform(...)` methods that parse raw params and call `transform_function(...)`.

### Stage 2: Registry and production wiring

Recommended model: `GPT-5.4`.

- Update `transforms/registry.py` to:
  - annotate registries as `dict[str, RegisteredPhraseTransform]` and `dict[str, RegisteredScoreTransform]`
  - pass `transform_function=...` to each definition
- Update `composition/transformer.py` to call registered transform `transform(...)`.
- Keep `composition/parser.py` using `parse_dimension(...)` for raw input normalization.
- Do not add dimension string parsing to transform params specs; internal transform requests should already contain `ToneDimension`.

### Stage 3: Pilot transforms

Recommended model: `GPT-5.4`.

- Convert a small representative set first:
  - `reverse` with `NoParams`
  - `drift` with `DriftParams`
  - one simple numeric transform such as `repeat` or `scale`
- Update their direct tests to pass typed params models where they bypass the registered transform.
- Run targeted tests and mypy after this stage before sweeping the rest of the transform modules.

### Stage 4: Remaining transform modules

Recommended model: `GPT-5.4 Mini`, after Stages 1-3 are green.

- Convert the remaining transforms by category:
  - basic
  - tempo
  - proportion
  - complexity
  - geological
  - counterpoint
- Move defaults out of transform functions and into `TransformParamFieldSpec.default`.
- Remove redundant local `isinstance` guards for params that are already parsed by the spec.

### Stage 5: Verification and cleanup

Recommended model: `GPT-5.4`. Use `GPT-5.5` only for hard type-design blockers, architectural mismatches, or a final high-confidence audit.

- Add or update tests for:
  - unknown params
  - missing required params
  - defaulted optional params
  - dimension params requiring already-normalized `ToneDimension`
  - custom validators running on typed params
  - registered transform `transform(...)`
- Keep raw string dimension normalization tests at the parser boundary. Direct transform tests should pass typed params models containing `ToneDimension`, not raw strings.
- Run targeted tests first, then coverage for touched modules, then the broader suite.
- Run mypy and ensure transform modules do not require local casts or `Any`.
- Check `drift.py` for any transform function that is not used in production code.

## Status

- [x] Add typed parsing to `ParamSchema`.
- [x] Add shared `NoParams`.
- [x] Add defaults to `TransformParamFieldSpec`.
- [x] Make `TransformParamsSpec[P]` generic with required typed `params_factory`.
- [x] Add `TransformParamsSpec.parse_params(...)` returning typed params.
- [x] Add `RegisteredPhraseTransform` and `RegisteredScoreTransform` Protocols.
- [x] Make `PhraseTransformDefinition` and `ScoreTransformDefinition` generic.
- [x] Rename stored callable field to `transform_function`.
- [x] Route production transform invocation through registered transform `transform(...)`.
- [x] Update registry definitions to use `transform_function=...`.
- [x] Remove stale `validate_params(...)` methods from transform definitions.
- [x] Keep raw dimension string normalization at the parser boundary, not in transform param parsing.
- [x] Add `ToneDimensionParam` for already-normalized internal dimension values.
- [x] Add `ParsedTransformParams` so factories build typed params without repeating schema validation.
- [ ] Define typed params models per remaining transform.
- [ ] Update remaining transform function signatures and remove redundant `isinstance` guards.
- [ ] Update remaining tests.
- [ ] Move `parse_dimension(...)` out of `transforms/base.py` if doing so keeps the parser boundary clearer.
- [ ] Check `drift.py` for any transform function that is not used in production code.

## Handoff Notes

### Current state

- This refactor is intentionally mid-migration. Broad test runs are expected to fail until all transform specs have `params_factory` and all registered transform functions accept typed params.
- `transforms/base.py` now has:
  - generic `ParamSchema[T].parse(...)`
  - `NoParams`
  - `ToneDimensionParam`, which accepts only already-normalized `ToneDimension` values and does not parse raw strings
  - `TransformParamFieldSpec.default`
  - generic `TransformParamsSpec[P]` with required `params_factory`
  - `ParsedTransformParams`, the post-schema parsed-value accessor passed to transform params factories
  - generic `PhraseTransformDefinition[P]` and `ScoreTransformDefinition[P]`
  - public definition `transform(...)` methods that parse raw params and call `transform_function(...)`
  - registry-facing `RegisteredPhraseTransform` and `RegisteredScoreTransform` Protocols
- `validate_transform_params(...)` and definition-level `validate_params(...)` were removed. Parsing now happens through `TransformParamsSpec.parse_params(...)` and registered definition `transform(...)`.
- The optional custom validator hook was removed under YAGNI. Reintroduce only when a real cross-field validation rule requires it.
- `composition/transformer.py` now calls registered definition `transform(...)` and no longer validates params separately.
- `transforms/registry.py` now uses `transform_function=...` and Protocol-typed registries.
- Transform factories now receive `ParsedTransformParams`, not `Mapping[str, object]`.
  - Field schemas own raw value validation and conversion.
  - Factories should call `parsed_params.required("field", ExpectedType)` and construct the params dataclass.
  - Do not add repeated local `isinstance` validation blocks in transform modules for fields already parsed by schemas.
- Converted transforms:
  - `reverse` uses `NoParams`.
  - `repeat` uses `RepeatParams(count: int)`.
  - `transpose` uses `TransposeParams(semitones: float)`.
  - `delay` uses `DelayParams(seconds: float)`.
  - `pad_silence` uses `PadSilenceParams(seconds: float, position: str)`.
  - `drift` uses `DriftParams(dimension: ToneDimension, rate: float)`.
  - `inversion` uses `InvertParams(dimension: ToneDimension)`.
  - `scale` uses `ScaleParams(dimension: ToneDimension, factor: float)`.
  - `cellular_automata` uses `CellularAutomataParams(dimension: ToneDimension, rule: int, generations: int, max_deviation: float)`.
  - `random_drop` uses `RandomDropParams(dimension: ToneDimension, max_drop_pct: int, drop_frequency_pct: int)`.
  - `weierstrass` uses `WeierstrassParams(dimension: ToneDimension, intensity: str)`.
  - `add_pedal_tone` uses `AddPedalToneParams(frequency: float)`.
  - `stretto` uses `StrettoParams(motif: str, num_times: int, spacing: str | float)`.
  - `erosion` uses `ErosionParams(dimension: ToneDimension)`.
  - `frost_effect` uses `FrostEffectParams(iterations: int)`.
  - `terraced_drift` uses `TerracedDriftParams(dimension: ToneDimension, max_step_change_pct: int)`.
  - `feigenbaum` uses `FeigenbaumParams(dimension: ToneDimension)`.
  - `golden_ratio` uses `GoldenRatioParams(dimension: ToneDimension)`.
  - `accelerando` and `ritardando` use `TempoChangeParams(strength: float, jaggedness: float)`.
- `MINIMUM_FREQUENCY_HZ = 0.0` now lives in `score_model/tone.py`.
  - `inversion` and `scale` use it instead of a hard-coded `1.0` frequency floor.
  - This preserves sub-audio positive frequencies as possible intermediate pipeline state while preventing negative frequencies.
- Recent focused verification:
  - `.venv/bin/mypy transforms/geological/terraced_drift.py tests/test_geological_modulation.py`
  - `.venv/bin/pytest tests/test_geological_modulation.py -q`
  - `.venv/bin/ruff check transforms/geological/terraced_drift.py tests/test_geological_modulation.py tests/test_transform_wrappers_behavior_happy_path.py tests/test_transform_wrappers_behavior_error_paths.py`
  - `.venv/bin/python -m py_compile transforms/geological/terraced_drift.py tests/test_geological_modulation.py tests/test_transform_wrappers_behavior_happy_path.py tests/test_transform_wrappers_behavior_error_paths.py`
  - `.venv/bin/mypy transforms/geological/frost_effect.py tests/test_frost_helpers.py`
  - `.venv/bin/pytest tests/test_frost_helpers.py -q`
  - `.venv/bin/pytest tests/test_frost_effect_edge_expansion.py -q`
  - `.venv/bin/ruff check transforms/geological/frost_effect.py tests/test_frost_helpers.py`
  - `.venv/bin/python -m py_compile transforms/geological/frost_effect.py tests/test_frost_helpers.py`
  - `.venv/bin/mypy transforms/geological/erosion.py tests/test_geological_erosion.py`
  - `.venv/bin/pytest tests/test_geological_erosion.py -q`
  - `.venv/bin/ruff check transforms/geological/erosion.py tests/test_geological_erosion.py`
  - `.venv/bin/python -m py_compile transforms/geological/erosion.py tests/test_geological_erosion.py`
  - `.venv/bin/mypy transforms/counterpoint/fugue.py`
  - `.venv/bin/python -m py_compile transforms/counterpoint/fugue.py tests/test_counterpoint_fugue.py`
  - `.venv/bin/ruff check transforms/counterpoint/fugue.py tests/test_counterpoint_fugue.py`
  - direct smoke check for `ADD_PEDAL_TONE_PARAMS_SPEC`, `STRETTO_PARAMS_SPEC`, `add_pedal_tone_score_transform(...)`, and `stretto_score_transform(...)`
  - `.venv/bin/mypy transforms/complexity/weierstrass.py transforms/complexity/random_drop.py`
  - `.venv/bin/pytest tests/test_complexity_transforms.py -q`
  - `.venv/bin/python -m py_compile transforms/complexity/weierstrass.py tests/test_complexity_transforms.py tests/test_transform_wrappers_behavior_happy_path.py tests/test_transform_wrappers_behavior_error_paths.py`
  - `.venv/bin/ruff check transforms/complexity/weierstrass.py tests/test_complexity_transforms.py tests/test_transform_wrappers_behavior_happy_path.py tests/test_transform_wrappers_behavior_error_paths.py`
  - `.venv/bin/mypy transforms/complexity/random_drop.py`
  - `.venv/bin/python -m py_compile transforms/complexity/random_drop.py tests/test_complexity_transforms.py tests/test_transform_wrappers_behavior_happy_path.py tests/test_transform_wrappers_behavior_error_paths.py`
  - `.venv/bin/ruff check transforms/complexity/random_drop.py tests/test_complexity_transforms.py tests/test_transform_wrappers_behavior_happy_path.py tests/test_transform_wrappers_behavior_error_paths.py`
  - `.venv/bin/mypy transforms/base.py transforms/basic/repeat.py transforms/basic/transpose.py transforms/basic/delay.py transforms/basic/pad_silence.py transforms/basic/drift.py transforms/basic/inversion.py transforms/basic/scale.py transforms/complexity/cellular_automata.py`
  - `.venv/bin/pytest tests/test_delay.py tests/test_scale.py tests/test_invert.py -q`
  - `py_compile` passed for `transforms/complexity/cellular_automata.py` and the wrapper behavior test files.
- Known current blocker:
  - `tests/test_drift.py -q` still fails during collection because `transforms/proportion/feigenbaum.py` is the next unconverted registry import and its `FEIGENBAUM_PARAMS_SPEC` is missing `params_factory`.
  - `tests/test_frost_effect_demo.py -q` and `tests/test_frost_effect_recursive_demo.py -q` fail on the same `feigenbaum` registry import blocker.

### Next small steps

1. Convert `transforms/proportion/feigenbaum.py` next.
   - Add a typed params dataclass and params factory.
   - Change `FEIGENBAUM_PARAMS_SPEC` to a generic `TransformParamsSpec[...]`.
   - Use `ToneDimensionParam()` for `dimension`.
   - Move defaults into `TransformParamFieldSpec.default`.
   - Update phrase/score wrapper signatures to accept typed params.
   - Move raw invalid-param wrapper tests to `FEIGENBAUM_PARAMS_SPEC.parse_params(...)`.
   - Run `tests/test_drift.py -q` again to find the next registry import blocker.
2. Continue through remaining unconverted transforms one at a time.
   - Current unconverted specs are the tempo/time transforms: `rubato` and anything else remaining.
3. Keep each step reviewable.
   - Convert one transform at a time.
   - Update only direct tests for that transform.
   - Run targeted tests for that transform, not the full suite until the migration is closer to complete.
4. Do not re-add parser-style dimension normalization in transform params.
   - Raw dimension strings belong in `composition/parser.py`.
   - Transform params should expect already-normalized `ToneDimension` for dimension-bearing transforms.

## Success Criteria

- Transform modules receive concrete params objects, not `Mapping[str, object]`.
- Mypy passes without local casts or `Any` in transform modules.
- Runtime validation errors still happen at the registered transform/spec boundary.
- Existing transform behavior is preserved.
