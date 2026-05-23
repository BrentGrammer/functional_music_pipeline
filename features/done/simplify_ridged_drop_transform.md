# Simplify Ridged Drop Transform

## Goal

Simplify the public API for `apply_ridged_drop_transform` so users can apply the transform without needing to understand the low-level ridged noise controls.

## Current Issue

The transform currently exposes several implementation-level parameters:

```python
def apply_ridged_drop_transform(
    tones,
    dimension,
    max_deviation,
    seed=42,
    octaves=3,
    ridge_density=0.3,
    drop_when_noise_above=0.5,
):
```

`octaves`, `ridge_density`, and `drop_when_noise_above` are useful internally, but they make the transform harder to use creatively from composition JSON.

`seed` is also too technical for the public JSON API. It gives users useful behavior because it allows repeatable stochastic variants, but the name and arbitrary number values do not clearly explain what users are controlling.

## Proposed API

Expose only the essential musical controls:

```python
def apply_ridged_drop_transform(
    tones: list[Tone],
    dimension: ToneDimension | str,
    drop_depth: float | str,
    intensity: str = "medium",
    new_pattern_each_use: bool = False,
) -> list[Tone]:
```

The public JSON-facing API should not expose `seed`. The transform should own its randomness policy internally while still giving users a clear way to request a new generated drop pattern when they reuse the same transform settings.

Example JSON:

```json
{
  "name": "ridged_drop",
  "params": {
    "dimension": "amplitude",
    "drop_depth": 0.8,
    "intensity": "medium",
    "new_pattern_each_use": true
  }
}
```

`new_pattern_each_use` behavior:

1. `false`: repeated uses with the same settings reuse the same internal drop pattern.
2. `true`: repeated uses with the same settings get a new generated drop pattern per occurrence.

## Preset Mapping

Replace the low-level public parameters with private intensity presets. `intensity` controls the shape, density, and threshold behavior of the ridged drop pattern.

It should replace:

1. `octaves`
2. `ridge_density`
3. `drop_when_noise_above`

Example preset map:

```python
_RIDGED_DROP_INTENSITY_PRESETS = {
    "subtle": {"octaves": 2, "ridge_density": 0.2, "drop_when_noise_above": 0.7},
    "medium": {"octaves": 3, "ridge_density": 0.3, "drop_when_noise_above": 0.5},
    "severe": {"octaves": 4, "ridge_density": 0.45, "drop_when_noise_above": 0.3},
}
```

Exact values should be adjusted by listening tests or snapshot tests.

## Drop Depth Policy

Rename public `max_deviation` to `drop_depth` for this transform.

Reason: `max_deviation` is technically accurate, but it is generic and does not describe what `ridged_drop` actually does. `drop_height` is more evocative, but `height` can imply upward movement or pitch height. `drop_depth` better communicates that the selected dimension is reduced.

Keep `drop_depth` separate from `intensity`.

Reason: `intensity` and `drop_depth` control different musical ideas.

1. `intensity`: how active, dense, or aggressive the generated ridged drop pattern is.
2. `drop_depth`: how far the selected tone dimension can fall once the pattern applies a drop.

`drop_depth` should accept both named presets and numeric values, matching the pattern used by tempo transforms.

Preset values:

```python
_RIDGED_DROP_DEPTH_LEVELS = {
    "none": 0.0,
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "extreme": 1.0,
}
```

Numeric values should be accepted from `0.0` to `1.0` for precise control.

Examples:

```json
"drop_depth": "medium"
```

```json
"drop_depth": 0.37
```

Keeping them separate lets users combine them musically. For example, a user can choose a dense pattern with shallow drops or a sparse pattern with deep drops.

Example:

```json
{
  "name": "ridged_drop",
  "params": {
    "dimension": "amplitude",
    "drop_depth": 0.3,
    "intensity": "severe",
    "new_pattern_each_use": true
  }
}
```

This means: use an active/severe drop pattern, but keep each individual drop relatively shallow.

If `drop_depth` were folded into `intensity`, users would lose that control.

Implementation detail: `drop_depth` can still be passed into the shared modulation helper as `max_deviation` internally. The rename is only for the public ridged-drop API.

## Implementation Checkpoints

The refactor should be implemented in small reviewable checkpoints. Stop after each checkpoint so the changes can be inspected before continuing.

### 1. Add Boolean Param Schema

Scope:

1. Add `BooleanParam` to `transforms/base.py` if one does not already exist.
2. Add tests proving boolean params accept only `true` and `false`, not integers, strings, or `None`.

Verification:

```shell
pytest tests/test_transforms_base.py
```

Stop for review.

### 2. Add Drop Depth Resolver

Scope:

1. Add `_RIDGED_DROP_DEPTH_LEVELS` in `transforms/geological/ridged_drop.py`.
2. Add `_resolve_drop_depth(value)`.
3. Support `none`, `low`, `medium`, `high`, `extreme`, and numeric values from `0.0` to `1.0`.
4. Reject booleans, unknown strings, numeric strings, values below `0.0`, and values above `1.0`.
5. Add focused geological modulation tests for the resolver.

Verification:

```shell
pytest tests/test_geological_modulation.py
```

Stop for review.

### 3. Add Intensity Presets

Scope:

1. Add `_RIDGED_DROP_INTENSITY_PRESETS` in `transforms/geological/ridged_drop.py`.
2. Add `_resolve_intensity(value)`.
3. Support `subtle`, `medium`, and `severe`.
4. Reject booleans, unknown strings, non-string values, and `None`.
5. Add focused geological modulation tests for the resolver.

Verification:

```shell
pytest tests/test_geological_modulation.py
```

Stop for review.

### 4. Refactor Ridged Drop Function Signature

Scope:

1. Change `apply_ridged_drop_transform` to accept `dimension`, `drop_depth`, `intensity="medium"`, and `new_pattern_each_use=False`.
2. Remove public `seed`, `octaves`, `ridge_density`, and `drop_when_noise_above` from the signature.
3. Resolve `drop_depth` to the internal `max_deviation` value passed to `apply_profile`.
4. Resolve `intensity` to internal `_RidgedMultifractalProfile` settings.
5. For this checkpoint, ignore `new_pattern_each_use` behavior and keep the existing fixed internal seed.

Verification:

```shell
pytest tests/test_geological_modulation.py
```

Stop for review.

### 5. Update Ridged Drop Params Spec

Scope:

1. Update `RIDGED_DROP_PARAMS_SPEC` to expose only `dimension`, `drop_depth`, `intensity`, and `new_pattern_each_use`.
2. Make `dimension` and `drop_depth` required.
3. Make `intensity` optional with default behavior handled by the function.
4. Make `new_pattern_each_use` optional with default `False` behavior handled by the function.
5. Use a union schema for `drop_depth`: supported depth enum or float.
6. Use an enum schema for `intensity`.
7. Use `BooleanParam` for `new_pattern_each_use`.
8. Add or update JSON parser validation tests for accepted new params and rejected old params.

Verification:

```shell
pytest tests/test_json_parser.py tests/test_transforms_base.py
```

Stop for review.

### 6. Update Existing Geological Tests

Scope:

1. Replace old test calls using `max_deviation` with `drop_depth`.
2. Remove old public `seed`, `octaves`, `ridge_density`, and `drop_when_noise_above` from test calls.
3. Remove or rewrite tests that depend on public `octaves=0` behavior.
4. Add tests proving string and numeric `drop_depth` values can produce equivalent results.
5. Add tests proving `intensity` changes the generated drop behavior.

Verification:

```shell
pytest tests/test_geological_modulation.py
```

Stop for review.

### 7. Update JSON Demos

Scope:

1. Update `compositions/geological_example.json`.
2. Replace `max_deviation` with `drop_depth` for `ridged_drop` only.
3. Remove `seed` from the `ridged_drop` entry.
4. Add `intensity` only where it improves the demo clarity. It can be omitted when `medium` is acceptable.
5. Do not update unrelated transforms in this checkpoint unless their tests require it.

Verification:

```shell
pytest tests/test_json_parser.py
```

Stop for review.

### 8. Implement New Pattern Each Use

Scope:

1. Identify where phrase and score transform occurrences are applied in the parser or orchestration layer.
2. Add internal occurrence-based seed derivation outside `apply_ridged_drop_transform` if feasible.
3. Keep `apply_ridged_drop_transform` stateless. Do not make it remember the previous seed.
4. When `new_pattern_each_use` is `False`, keep deterministic default behavior.
5. When `new_pattern_each_use` is `True`, repeated transform occurrences with the same public settings should receive distinct generated drop patterns.
6. Add tests proving same settings can produce distinct patterns across separate occurrences when `new_pattern_each_use` is `True`.

Verification:

```shell
pytest tests/test_geological_modulation.py tests/test_json_parser.py
```

Stop for review.

### 9. Final Focused Test Pass

Scope:

1. Run the focused tests for the refactor.
2. Fix only issues directly related to this refactor.

Verification:

```shell
pytest tests/test_geological_modulation.py tests/test_json_parser.py tests/test_transforms_base.py
```

Stop for final review.

## Seed Policy

Removing `seed` from the public API makes composition JSON simpler and keeps the transform focused on musical controls.

Reasons to expose a seed would be:

1. Reproducing the exact same generated result across runs.
2. Sharing a composition where stochastic details must be identical for another user.
3. Debugging or snapshot testing stochastic behavior.

Recommended direction: do not expose `seed` in composition JSON. If deterministic output is desired, keep a private fixed seed internally. If varied output is desired, derive randomness internally outside the user-facing params.

## New Pattern Policy

`new_pattern_each_use` preserves the useful part of seeds without exposing arbitrary seed numbers.

This should not be implemented by making `apply_ridged_drop_transform` remember the previous seed. That would make the transform stateful and would conflict with the project's preference for stateless transformations.

Recommended direction: keep the transform pure. When `new_pattern_each_use` is `true`, the parser or orchestration layer should assign an internal occurrence identity and derive a seed from that identity. For example, the first, second, and third `ridged_drop` occurrences can receive distinct internal seeds without the user seeing or managing those seed values.

Practical user meaning:

```text
Use the same ridged-drop settings, but when I use this transform again, generate a new drop pattern for that use.
```

## Open Question

This should be a clean breaking simplification.

There are no external users or compatibility requirements, so the implementation should not retain old behavior just to make existing JSON files continue working.

Do not add backwards-compatibility support for:

1. `seed`
2. `octaves`
3. `ridge_density`
4. `drop_when_noise_above`

Any existing demos or tests that use those fields should be updated to the new public API instead.

## Demo Files

Run the following command inside the Docker container to generate WAV output for all demo files:

```shell
for file in compositions/*_demo.json; do name="$(basename "$file" .json)"; python main.py --composition-file "$file" --output-name "$name"; done
```

Or to generate only the new demo files added for this feature:

```shell
for file in compositions/invert_demo.json compositions/repeat_demo.json compositions/ritardando_demo.json compositions/feigenbaum_sequence_demo.json compositions/phrase_feigenbaum_shrink_demo.json compositions/phrase_feigenbaum_grow_demo.json compositions/score_feigenbaum_sequence_demo.json compositions/pedal_point_demo.json compositions/stretto_demo.json compositions/random_drop_demo.json compositions/score_cellular_automata_demo.json compositions/score_terraced_drift_demo.json compositions/score_ridged_drop_demo.json; do name="$(basename "$file" .json)"; python main.py --composition-file "$file" --output-name "$name"; done
```
