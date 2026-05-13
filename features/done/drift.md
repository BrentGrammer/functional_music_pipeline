# Feature: Drift Transform

## Status

Complete. The `drift` transform is implemented in `src/transforms/drift.py`, registered in `src/composition/parser.py`, covered by `src/tests/test_drift.py`, and demonstrated by the drift composition examples in `src/compositions/`.

## Overview

The `drift` transform handles directional shifting of musical dimensions via a `rate` parameter. It separates smooth growth or movement away from an origin from the destructive collapse behavior of the existing `erosion` transform.

## Naming Rationale

- **`erosion`**: Implies wearing away, breaking down, or collapsing.
- **`drift`**: Implies smooth movement away from an origin. It works for both decay-like movement and growth-like movement.

## Relationship to Erosion

### `erosion`

Keeps the destructive or collapse behaviors:

- **FREQUENCY**: Collapses all tones toward the frequency of the first tone.
- **AMPLITUDE**: Applies a linear fade-out to silence.
- **DURATION**: Iteratively removes the last tone.

### `drift`

Handles directional shifting via a `rate` parameter:

- **FREQUENCY**: Progressively shifts each frequency by a linear step.
- **AMPLITUDE**: Progressively shifts each amplitude by a linear step.
- **DURATION**: Progressively shifts each duration by a linear step.

## Rate Semantics

The `rate` parameter expresses the per-step shift as a fraction of the first tone's value in the chosen dimension. The drift is additive and linear, not multiplicative.

For a phrase `[T0, T1, T2, ...]` and a rate `r`:

- `step = T0.value * r`
- Output tone at index `i` has value `Ti.value + step * (i + 1)`

The drift is applied immediately beginning with tone 0. The first output tone is already shifted by one step, producing a pronounced effect from the start of the phrase.

## Direction by Dimension

- **FREQUENCY**: Positive rate creates an upward glissando; negative rate creates a downward glissando.
- **AMPLITUDE**: Positive rate creates a crescendo; negative rate creates a diminuendo.
- **DURATION**: Positive rate creates a ritardando by making tones longer; negative rate creates an accelerando by making tones shorter.
- **ZERO RATE**: Leaves the selected dimension unchanged.

Amplitude is clamped to the range `0.0` through `1.0`. Duration is clamped at a minimum of `0.0`.

## Examples

- `rate: 0.05` on frequencies `[440, 440, 440]` uses `step = 22` and produces `[462, 484, 506]`.
- `rate: -0.05` on frequencies `[440, 440, 440]` uses `step = -22` and produces `[418, 396, 374]`.
- `rate: 0` is an identity transform.

## Parser Registration

The transform is available at two scopes:

- **`drift`**: Phrase-level transform registered with `TransformScope.PHRASE`.
- **`score_drift`**: Score-level transform registered with `TransformScope.SCORE_ALL_VOICES`, applying the same drift behavior across every voice in the score.

## Usage in Composition JSON

### Downward Frequency Drift

```json
{
  "name": "drift",
  "params": {
    "dimension": "FREQUENCY",
    "rate": -0.05
  }
}
```

### Upward Amplitude Drift

```json
{
  "name": "drift",
  "params": {
    "dimension": "AMPLITUDE",
    "rate": 0.05
  }
}
```

### Score-Level Drift

```json
{
  "name": "score_drift",
  "params": {
    "dimension": "FREQUENCY",
    "rate": 0.1
  }
}
```

## Demo Compositions

- `src/compositions/drift_demo.json`
- `src/compositions/drift_frequency_demo.json`
- `src/compositions/drift_frequency_negative_demo.json`
- `src/compositions/drift_amplitude_demo.json`
- `src/compositions/drift_amplitude_negative_demo.json`
- `src/compositions/drift_duration_demo.json`
- `src/compositions/drift_duration_negative_demo.json`
- `src/compositions/drift_score_demo.json`
