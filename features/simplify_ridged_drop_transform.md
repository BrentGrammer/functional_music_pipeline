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
    tones: ToneSequence,
    dimension: ToneDimension | str = ToneDimension.AMPLITUDE,
    max_deviation: float = 0.5,
    intensity: str = "medium",
    new_pattern_each_use: bool = False,
) -> ToneSequence:
```

The public JSON-facing API should not expose `seed`. The transform should own its randomness policy internally while still giving users a clear way to request a new generated drop pattern when they reuse the same transform settings.

Example JSON:

```json
{
  "name": "ridged_drop",
  "params": {
    "dimension": "amplitude",
    "max_deviation": 0.8,
    "intensity": "medium",
    "new_pattern_each_use": true
  }
}
```

`new_pattern_each_use` behavior:

1. `false`: repeated uses with the same settings reuse the same internal drop pattern.
2. `true`: repeated uses with the same settings get a new generated drop pattern per occurrence.

## Preset Mapping

Replace the low-level public parameters with private intensity presets, for example:

```python
_RIDGED_DROP_INTENSITY_PRESETS = {
    "subtle": {"octaves": 2, "ridge_density": 0.2, "drop_when_noise_above": 0.7},
    "medium": {"octaves": 3, "ridge_density": 0.3, "drop_when_noise_above": 0.5},
    "severe": {"octaves": 4, "ridge_density": 0.45, "drop_when_noise_above": 0.3},
}
```

Exact values should be adjusted by listening tests or snapshot tests.

## Implementation Steps

1. Add a private preset mapping in `transforms/geological/ridged_drop.py`.
2. Update `apply_ridged_drop_transform` to accept `intensity` and `new_pattern_each_use` instead of public `seed`, `octaves`, `ridge_density`, and `drop_when_noise_above`.
3. Update `RIDGED_DROP_PARAMS_SPEC` to expose only `dimension`, `max_deviation`, `intensity`, and `new_pattern_each_use`.
4. Validate that `intensity` is one of the supported preset names.
5. Add boolean parameter validation for `new_pattern_each_use` if the params system does not already have a boolean schema.
6. Keep deterministic behavior when `new_pattern_each_use` is `false`.
7. Have the composition orchestration layer derive or inject an internal unique seed per transform occurrence when `new_pattern_each_use` is `true`.
8. Update geological modulation tests to use the simplified API.
9. Update JSON demos that currently pass `seed`.
10. Run the relevant test suite for geological transforms and JSON parser validation.

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
