# Stochastic Tempo Curve Transform

## Concept
A duration-focused transform where a phrase speeds up or slows down overall, while the individual tone-to-tone duration changes vary stochastically instead of following a strict linear ramp.

## Working Transform Name
`stochastic_tempo_curve`

## Initial Parameters To Discuss
*   `direction`: `accelerando` or `ritardando`
*   `curve`: controls the overall acceleration/deceleration shape
*   `jaggedness`: controls local stochastic variation, asymmetry, and possible local reversals between tones

Keep `seed` out of the first public API.

## Core Behavior
The transform should be capable of highly asymmetric duration distributions. For example, a five-tone accelerando should be able to produce a phrase where the first tone is much longer than the rest, while interior tones may still be unexpectedly short or long relative to their neighbors.

The output should preserve the overall directional identity:
*   `accelerando`: generally front-heavy, tending toward shorter durations later in the phrase
*   `ritardando`: generally back-heavy, tending toward longer durations later in the phrase

Local tone-to-tone relationships do not need to be monotonic. The stochastic component should be strong enough to create local surprises without erasing the larger phrase-level direction.

## Implementation Direction
Do not assume yet that this transform must preserve total phrase duration. Preserving total duration may be useful for alignment, but it may also make the user think too much about the phrase's total length. The preferred user experience is that the user writes the tones they want, applies the transform, and hears an effect without needing to calculate or plan the total phrase duration.

Two implementation paths were considered:

*   **Dedicated stochastic tempo curve**: Generate duration weights from an overall curve plus jaggedness. This can produce strong asymmetry, especially if the weights are normalized or otherwise shaped carefully.
*   **Jagged drift extension**: Reuse the existing `drift` transform's long-term linear trend and add a `jaggedness` parameter for stochastic local variation. This would make stochastic accelerando/ritardando an extension of the existing duration drift behavior.

Current decision: do not directly reuse the existing duration `drift` behavior for the musical wrappers. Existing duration drift is additive and bases its step on the first tone's duration, which can behave poorly when the input phrase already has uneven durations. The wrappers should use a duration-specific proportional model instead:

```text
new_duration = original_duration * trend_factor_at_index * jagged_weight
```

This keeps uneven source durations meaningful while still applying an overall accelerando or ritardando effect.

## Drift Reuse Concern
Directly reusing low-level duration `drift` is risky for uneven input durations.

The existing `drift` transform provides a global additive trend:
*   negative duration rate: accelerando, durations generally decrease
*   positive duration rate: ritardando, durations generally increase

But its duration formula is based on the first tone:

```text
new_duration = original_duration + (first_duration * raw_rate * (index + 1))
```

That can collapse later short tones or distort uneven phrases unexpectedly. Since the reference material already uses uneven durations, the wrappers should not be thin calls to current duration drift.

Design requirements for the proportional tempo model:
*   `jaggedness: 0` preserves a smooth proportional accelerando or ritardando.
*   Higher `jaggedness` values allow local reversals.
*   High `jaggedness` values allow strong asymmetry, including one tone being much longer than nearby tones.
*   The long-term direction should be statistically favored, not strictly monotonic.
*   Do not preserve total duration by default; this should behave like an effect applied to the phrase rather than a normalized redistribution of the phrase's original duration.
*   Avoid treating jaggedness as a small additive random offset. It should shape durations multiplicatively through stochastic weights:

```text
new_duration = original_duration * trend_factor_at_index * jagged_weight
```

## Jaggedness API Shape
Decision: allow `jaggedness` to accept either a named preset string or a numeric value. String presets are mapped internally to numeric settings.

Numeric API:

```json
{
  "name": "accelerando",
  "params": {
    "strength": 0.5,
    "jaggedness": 0.8
  }
}
```

Preset API:

```json
{
  "name": "accelerando",
  "params": {
    "strength": "medium",
    "jaggedness": "high"
  }
}
```

Named presets such as `low`, `medium`, and `high` may be easier for users because the system can map them to controlled internal numeric ranges. Numeric values give finer control but require users to understand the scale.

Proposed preset mapping:

```text
none    -> 0.0
low     -> 0.25
medium  -> 0.5
high    -> 0.75
extreme -> 1.0
```

Numeric values should use a public range of `0.0` to `1.0`. Treat the number as a percentage of available jaggedness intensity:

```text
0.0 = 0% jaggedness intensity; smooth proportional tempo behavior
0.5 = 50% jaggedness intensity
1.0 = 100% jaggedness intensity; maximum jaggedness range available from the transform
```

The implementation can map those public values to whatever internal stochastic weight range sounds appropriate.

## Musical Tempo Wrappers
Add musical transforms so users can express tempo intent directly:

```text
accelerando(strength, jaggedness)
ritardando(strength, jaggedness)
```

This avoids requiring users to know the low-level duration drift semantics.

For these wrappers, `strength` should not expose the raw low-level drift rate directly. Instead, it should be a constrained musical control from `0.0` to `1.0`, or a named preset string, describing how pronounced the duration change is across the phrase:

```text
0.0 = no duration change
0.25 = low duration change
0.5 = medium duration change
0.75 = high duration change
1.0 = extreme duration change
```

Use the same preset labels as `jaggedness`:

```text
none    -> 0.0
low     -> 0.25
medium  -> 0.5
high    -> 0.75
extreme -> 1.0
```

The wrapper should map this public strength to a proportional trend factor range. For `accelerando`, safe means preventing durations from collapsing to zero. For `ritardando`, very long durations can be musically valid, so the wrapper should not impose an arbitrary "too long" limit. Existing total-duration safeguards should handle truly excessive output.

Decision: both wrapper parameters, `strength` and `jaggedness`, should accept either numeric values or named preset strings. String presets are convenience labels that the implementation maps to internal numeric settings. Consider this shared preset convention for other future transforms, but treat that as a separate design discussion.

Invalid strings or numeric values outside `0.0` to `1.0` should raise clear `ValueError`s. Error messages should include a helpful usage tip listing the accepted presets and numeric range.

```json
{
  "name": "accelerando",
  "params": {
    "strength": "high",
    "jaggedness": 0.5
  }
}
```

## Reference Example
`src/compositions/monumentvalley.json` contains a hand-authored theme that approximates the desired accelerando behavior:

```text
durations: 0.9, 0.5, 0.6, 0.4, 0.3, 0.5, 0.4, 0.3, 0.2
```

This is the target feel for the proportional tempo transform: the phrase is front-heavy and speeds up overall, but local duration relationships are irregular. The first tone can be much longer than the rest, and later tones can still unexpectedly lengthen or shorten relative to nearby tones.

Two manual simulation demos provide reference models for expected output character:

*   `src/compositions/stochastic_tempo_irregularity_low_demo.json`: low jaggedness, mostly smooth accelerando with mild unevenness
*   `src/compositions/stochastic_tempo_irregularity_high_demo.json`: high jaggedness, front-heavy accelerando with strong local reversals and asymmetry

These demos should be used as qualitative targets, not exact expected outputs. The implemented transform will be stochastic, so generated durations may differ from run to run while preserving a similar overall character.

## Iterative Implementation Plan
1.  Add resolver helpers for shared preset-or-number controls.
    *   `strength` accepts `none`, `low`, `medium`, `high`, `extreme`, or a numeric value from `0.0` to `1.0`.
    *   `jaggedness` accepts `none`, `low`, `medium`, `high`, `extreme`, or a numeric value from `0.0` to `1.0`.
    *   Invalid strings or out-of-range numbers should raise clear `ValueError`s with usage guidance.
    *   Resolver helpers should live next to the proportional tempo transforms.
    *   Use separate resolver functions for `strength` and `jaggedness`, even though they share the same preset map.
    *   Do not accept numeric strings such as `"0.75"` yet.
    *   Reject booleans explicitly.
    *   Defaults: `strength="medium"`, `jaggedness="none"`.

    Step 1 breakdown:
    1.1.  Add a shared preset map near the proportional tempo transform code:
        ```text
        none    -> 0.0
        low     -> 0.25
        medium  -> 0.5
        high    -> 0.75
        extreme -> 1.0
        ```
    1.2.  Add `resolve_strength(value)` with default `medium`.
    1.3.  Add `resolve_jaggedness(value)` with default `none`.
    1.4.  For each resolver, accept preset strings case-insensitively.
    1.5.  For each resolver, accept numeric `int` / `float` values only when they are between `0.0` and `1.0`.
    1.6.  For each resolver, reject booleans before numeric checks.
    1.7.  For each resolver, reject numeric strings for now.
    1.8.  Raise helpful `ValueError`s for invalid presets, invalid types, and out-of-range numbers. Example message shape:
        ```text
        Invalid jaggedness: 'wild'. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0.
        ```
    1.9.  Add focused resolver unit tests before changing tempo transform behavior.

2.  Define the safe internal strength-to-trend-factor mapping.
    *   For `accelerando`, the highest public strength must not collapse durations to zero.
    *   For `ritardando`, do not impose an arbitrary maximum phrase length beyond the system's existing total-duration safeguards.

    Step 2 breakdown:
    2.1.  Decide the trend-factor model:
        ```text
        new_duration = original_duration * trend_factor_at_index
        ```
    2.2.  Define the neutral behavior:
        ```text
        strength = 0.0 -> every trend factor is 1.0
        ```
    2.3.  Define the strongest accelerando target. At `strength=1.0`, the final tone should remain audible and should not collapse to zero. Choose a minimum final-duration factor such as:
        ```text
        final accelerando factor = 0.10
        ```
        This means the last tone can become as short as 10% of its original duration at maximum strength before jaggedness is applied.
    2.4.  Define the strongest ritardando target. At `strength=1.0`, allow a large final-duration expansion without imposing an arbitrary musical maximum. Choose an initial practical factor such as:
        ```text
        final ritardando factor = 2.0
        ```
        This can be adjusted later by listening tests; existing total-duration safeguards handle extreme output.
    2.5.  Map public `strength` linearly between neutral and the strongest target factors.
        *   `accelerando`: factors move from `1.0` toward the minimum final factor.
        *   `ritardando`: factors move from `1.0` toward the maximum final factor.
    2.6.  Apply trend factors across tone positions from first tone to last tone.
        *   Single-tone phrases should stay unchanged or use a factor of `1.0`.
        *   Multi-tone phrases should compute progress as `index / (tone_count - 1)`.
    2.7.  Keep the first tone's trend factor at or near `1.0` so the tempo change develops across the phrase rather than immediately altering the first tone dramatically.
    2.8.  Add focused tests for the mapping before adding jaggedness.
        *   `strength=0.0` produces all factors `1.0`.
        *   Maximum accelerando never produces a zero or negative trend factor.
        *   Maximum ritardando produces increasing trend factors.
        *   Uneven original durations are scaled proportionally, not additively.

3.  Add musical proportional tempo transforms.
    *   `accelerando(tones, strength=..., jaggedness=...)`
    *   `ritardando(tones, strength=..., jaggedness=...)`
    *   Do not delegate directly to current duration `drift`.
    *   Apply proportional trend factors across tone positions.
    *   `accelerando` maps public `strength` to decreasing trend factors.
    *   `ritardando` maps public `strength` to increasing trend factors.

    Step 3 breakdown:
    3.1.  Decide the implementation location for the new transforms.
        *   Prefer a new transform module if the proportional tempo logic grows beyond simple drift helpers.
        *   Keep resolver helpers and trend-factor helpers close to the transform functions.
    3.2.  Add a private helper to apply trend factors to tone durations while preserving frequency, sample rate, and amplitude.
    3.3.  Add `accelerando_transform(tones, strength="medium", jaggedness="none")`.
        *   Resolve `strength`.
        *   Compute decreasing trend factors.
        *   Apply proportional duration scaling.
    3.4.  Add `ritardando_transform(tones, strength="medium", jaggedness="none")`.
        *   Resolve `strength`.
        *   Compute increasing trend factors.
        *   Apply proportional duration scaling.
    3.5.  Keep `jaggedness` in the function signatures but treat `none` / `0.0` as the only implemented behavior until step 4.
        *   If a non-zero `jaggedness` is passed before step 4 is implemented, either ignore it temporarily in the branch or raise a clear not-yet-supported error during development.
    3.6.  Handle empty and single-tone phrases.
        *   Empty input returns `[]`.
        *   Single-tone input should remain unchanged for smooth trend behavior.
    3.7.  Add unit tests for smooth proportional behavior.
        *   `accelerando` decreases durations across an even-duration phrase.
        *   `ritardando` increases durations across an even-duration phrase.
        *   Uneven input durations are scaled proportionally.
        *   Other tone fields are preserved.
    3.8.  Listening checkpoint: render simple smooth `accelerando` and `ritardando` examples with `jaggedness="none"`.
        *   Confirm the effect is audible and directional.
        *   Confirm uneven source durations still sound musically related to the original phrase.

4.  Add jaggedness to the proportional tempo transforms.
    *   Default `jaggedness` should be `none` / `0.0`, preserving smooth proportional behavior.
    *   Jaggedness should apply as a multiplicative stochastic weight after the trend factor.
    *   The stochastic weighting should allow local reversals and strong asymmetry at high jaggedness.

    Step 4 breakdown:
    4.1.  Resolve `jaggedness` inside `accelerando_transform` and `ritardando_transform`.
    4.2.  Define the stochastic weight model.
        *   Use multiplicative weights, not additive offsets.
        *   `jaggedness=0.0` should always produce weight `1.0`.
    4.3.  Choose an internal weight range for maximum jaggedness.
        *   The range should be wide enough to create local reversals and strong asymmetry.
        *   The public `0.0` to `1.0` jaggedness value maps into this internal range.
    4.4.  Decide how randomness is controlled for tests without exposing `seed` in the public JSON API.
        *   Prefer an optional internal/test-only random source or seed parameter in Python.
        *   Do not document `seed` as part of the first public composition API.
    4.5.  Apply jagged weights after the smooth trend factor:
        ```text
        new_duration = original_duration * trend_factor_at_index * jagged_weight
        ```
    4.6.  Protect against invalid duration output.
        *   Durations should not become negative.
        *   Accelerando output should not collapse to zero.
        *   Very short but audible durations may be allowed if they support the intended jagged effect.
    4.7.  Verify local reversals are possible.
        *   High jaggedness should be able to make a later duration longer than a nearby earlier duration during accelerando.
        *   High jaggedness should be able to make a later duration shorter than a nearby earlier duration during ritardando.
    4.8.  Add focused jaggedness tests.
        *   `jaggedness=0.0` matches smooth proportional output.
        *   Preset and numeric jaggedness values resolve correctly.
        *   Controlled randomness can produce local reversals.
        *   Other tone fields are preserved.
    4.9.  Listening checkpoint: render low, medium, high, and extreme jaggedness examples.
        *   Confirm low jaggedness stays close to smooth behavior.
        *   Confirm high/extreme jaggedness can create local reversals and asymmetry.
        *   Compare against the Monument Valley reference feel.

5.  Register parser names.
    *   Add phrase transforms: `accelerando`, `ritardando`.
    *   Consider score-level wrappers later if phrase-level behavior works well.

    Step 5 breakdown:
    5.1.  Import the new transform functions in `src/composition/parser.py`.
    5.2.  Register `accelerando` as a `TransformScope.PHRASE` transform.
    5.3.  Register `ritardando` as a `TransformScope.PHRASE` transform.
    5.4.  Verify JSON params are passed through as keyword arguments:
        ```json
        {
          "name": "accelerando",
          "params": {
            "strength": "high",
            "jaggedness": "medium"
          }
        }
        ```
    5.5.  Add parser/integration tests showing both transforms can be invoked from composition JSON.
    5.6.  Do not add `score_accelerando` or `score_ritardando` in the first pass.
        *   Revisit score-level wrappers after phrase-level behavior is validated.
    5.7.  Listening checkpoint: render the JSON-invoked transforms, not just direct Python calls.
        *   Confirm parser usage produces the same kind of result as direct transform usage.

6.  Add focused tests.
    *   Existing `drift` tests must still pass unchanged.
    *   `accelerando` with numeric and preset `strength` should shorten durations without collapsing to zero.
    *   `ritardando` with numeric and preset `strength` should lengthen durations.
    *   Uneven input durations should remain meaningful under proportional scaling.
    *   `jaggedness: 0` should be deterministic and smooth.
    *   High jaggedness should be capable of local reversals with a controlled/randomized test setup.

    Step 6 breakdown:
    6.1.  Add resolver tests.
        *   Preset strings resolve correctly.
        *   Presets are case-insensitive.
        *   Numeric values from `0.0` to `1.0` resolve correctly.
        *   Numeric strings are rejected.
        *   Booleans are rejected.
        *   Invalid strings and out-of-range numbers raise helpful `ValueError`s.
    6.2.  Add smooth `accelerando` tests with `jaggedness="none"`.
        *   Durations generally decrease.
        *   No duration collapses to zero at maximum `strength`.
        *   Empty and single-tone inputs behave as specified.
    6.3.  Add smooth `ritardando` tests with `jaggedness="none"`.
        *   Durations generally increase.
        *   Very long durations are not arbitrarily blocked by the transform.
        *   Empty and single-tone inputs behave as specified.
    6.4.  Add uneven-duration tests.
        *   Confirm scaling is proportional, not additive.
        *   Confirm short later notes are not collapsed just because the first tone is long.
    6.5.  Add jaggedness tests.
        *   `jaggedness="none"` and `jaggedness=0.0` match smooth output.
        *   High jaggedness can produce local reversals with controlled randomness.
        *   High jaggedness preserves valid positive durations.
    6.6.  Add parser tests.
        *   `accelerando` can be invoked from JSON with numeric params.
        *   `accelerando` can be invoked from JSON with preset params.
        *   `ritardando` can be invoked from JSON with numeric params.
        *   `ritardando` can be invoked from JSON with preset params.
    6.7.  Run existing regression tests for `drift`, parser behavior, and duration-related transforms.
    6.8.  Listening checkpoint: after tests pass, render a small fixed set of comparison files.
        *   Smooth accelerando
        *   Smooth ritardando
        *   Low jaggedness accelerando
        *   High jaggedness accelerando
        *   High jaggedness ritardando

7.  Add or update example compositions.
    *   Keep the low/high jaggedness manual demos as qualitative references.
    *   Add runnable examples using the real `accelerando` and `ritardando` wrappers once implemented.
    *   Final listening checkpoint: compare implemented examples against `monumentvalley.json` and the manual low/high jaggedness demos.

## Items to Revisit

*   Add tests for `random_source` parameter in `_compute_jaggedness_weights` (from step 4.4)
*   Verify `max_weight_range = 0.5` is appropriate via listening tests (from step 4.3)
