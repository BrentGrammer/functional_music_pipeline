# Simplify Transform Public API

## Goal

Reduce the complexity of the public API for transforms. Users should be able to use transforms creatively without needing to understand implementation details. This includes:

1. Removing `seed` parameters entirely (deterministic by default, randomness handled internally)
2. Replacing technical parameters with intuitive presets
3. Keeping parameters minimal: ideally 2-3 required parameters, at most 1 optional parameter

## Guiding Principles

1. **Musical intent over implementation**: Parameters should describe what the user wants musically, not how the algorithm works internally.
2. **Presets over numbers**: Named presets (e.g., "subtle", "medium", "severe") are easier to understand than arbitrary numeric values.
3. **Minimal API surface**: Every parameter must justify its existence. If in doubt, leave it out.
4. **Sensible defaults baked in**: Rather than exposing optional parameters with defaults, pick the best default and hide the complexity.
5. **Consistency**: Similar transforms should have similar APIs.

## Target API Complexity

| Complexity | Parameters | Example |
|------------|------------|---------|
| Ideal | 2 required, 0 optional | `dimension`, `intensity` |
| Acceptable | 2-3 required, 0-1 optional | `dimension`, `depth`, optional `texture` |
| Too complex | 4+ parameters | Needs simplification |

---

## Part 1: Remove Seed from Public API

### Background

The `seed` parameter is an implementation detail. Users should not see it. Transforms will use a fixed internal seed (42) for deterministic, reproducible behavior by default.

**Decision**: Remove `new_pattern_each_use` as well. If a user wants variation, they should apply the transform multiple times with different presets, not toggle a randomness flag. This keeps the API simpler.

If we later need per-call randomness, we can add a global composition-level setting rather than per-transform flags.

### Affected Transforms

| Transform | Action |
|-----------|--------|
| `weierstrass` | Remove `seed`, use internal fixed seed |
| `cellular_automata` | Remove `seed` entirely (internal and public) — derive initial state from input tones |
| `random_drop` | Remove `seed`, use internal fixed seed |
| `terraced_drift` | Remove `seed`, use internal fixed seed |
| `accelerando` / `ritardando` | Remove `seed`, use internal fixed seed |

---

## Part 2: Simplify Overly Complex Transforms

### `weierstrass` - Currently 6 Parameters

**Current API:**
- `dimension` (required)
- `max_deviation` (required)
- `seed` (optional)
- `amplitude_scaling` (optional)
- `ripples_per_wave` (optional)
- `iterations` (optional)

**Proposed API (2 required, 0 optional):**
- `dimension` (required): `"frequency"` | `"duration"` | `"amplitude"`
- `intensity` (required): `"low"` | `"medium"` | `"high"` | `"extreme"`

The `intensity` preset controls both the deviation amount AND the texture characteristics. Users pick how much weierstrass wobble they want, and the preset handles all the internal tuning.

**Preset mapping:**
```python
_WEIERSTRASS_INTENSITY_PRESETS = {
    "low": {"max_deviation": 0.05, "amplitude_scaling": 0.3, "ripples_per_wave": 2.0, "iterations": 6},
    "medium": {"max_deviation": 0.15, "amplitude_scaling": 0.5, "ripples_per_wave": 3.0, "iterations": 10},
    "high": {"max_deviation": 0.25, "amplitude_scaling": 0.6, "ripples_per_wave": 4.0, "iterations": 12},
    "extreme": {"max_deviation": 0.4, "amplitude_scaling": 0.8, "ripples_per_wave": 6.0, "iterations": 18},
}
```

**Why max_deviation caps at 0.4 and never reaches 1.0:**

The modulation formula is `scale = 1.0 + (profile_value * max_deviation)`. The profile produces values between -1.0 and 1.0. At `max_deviation=1.0`, the scale could reach 0.0 — completely zeroing out a tone's frequency, amplitude, or duration. That's destructive, not textural. At 0.4, even the most extreme wobble only modifies tones by ±40%, keeping everything musically coherent and tones recognizable.

---

### `cellular_automata` - Currently 5 Parameters

**Current API:**
- `dimension` (required)
- `max_deviation` (required)
- `rule` (optional)
- `seed` (optional)
- `width` (optional)

**Problems with current implementation:**

The current implementation uses `seed` to randomly generate an initial binary state, then evolves it with the CA rule. This is fundamentally wrong — cellular automata are deterministic systems with sensitivity to initial conditions (SDIC). The initial state should come from the input tones, not from a PRNG. The `width` parameter is also artificial; it should be derived from the number of input tones.

**Design philosophy:**

Cellular automata exhibit sensitivity to initial conditions — small differences in the starting pattern produce dramatically different evolutions. The transform should exploit this by using the *musical input itself* as the initial condition. The CA rule then deterministically reshapes that pattern. This is honest to the mathematical concept: the music IS the automaton's initial state, the rule transforms it, and the evolved state maps back onto the music.

**How it works internally:**

1. **Derive initial state from input tones**: Extract the target dimension's values from all tones, compute the median, threshold into binary (>= median → 1, < median → 0). This gives one cell per tone.
2. **Evolve for K generations**: Apply the CA rule K times. The spatial state (width = number of tones) evolves deterministically.
3. **Read final state directly**: The evolved binary state maps 1:1 back to tones as modulation values (-1.0 or 1.0 per cell, scaled by max_deviation).

No RNG. No seed. No arbitrary width. The number of generations (K) controls how far the pattern diverges from the input's original structure — this is the "intensity" knob.

**Proposed API (3 required, 0 optional):**
- `dimension` (required): `"frequency"` | `"duration"` | `"amplitude"`
- `rule` (required): Wolfram rule number (0-255), e.g. 30, 90, 110
- `max_deviation` (required): how strongly the CA pattern modulates the tones (e.g. 0.3 = up to 30% deviation)

Internally, a fixed number of generations is used to evolve the state. This could be exposed later if needed, but for now a sensible default (e.g., 5-8 generations) keeps the API minimal.

**Edge cases:**
- All tones have the same value in the target dimension → fallback to alternating `[1,0,1,0...]` to give the rule a non-trivial starting pattern
- Single tone → return unchanged (CA needs spatial structure)
- Two tones → CA will function but behavior is trivial with wrap-around on 2 cells

---

### `terraced_drift` - Currently 5 Parameters

**Current API:**
- `dimension` (required)
- `max_deviation` (required)
- `seed` (optional)
- `step_size` (optional)
- `quantize_resolution` (optional)

**Proposed API (2 required, 0 optional):**
- `dimension` (required): `"frequency"` | `"duration"` | `"amplitude"`
- `max_step_change_pct` (required): the maximum percentage each tone can change from the previous tone (1-100). E.g., 10 = up to 10% change per step.

**Removed:**
- `seed` — removed entirely, use fixed internal seed for deterministic behavior
- `max_deviation` — derived internally from `max_step_change_pct` (they're highly correlated in practice; the original presets always set them to nearly the same value)
- `step_size` — replaced by `max_step_change_pct` (same concept, clearer name and scale)
- `quantize_resolution` — derived internally from `max_step_change_pct`

---

### `random_drop` - Currently 4 Parameters

**Current API:**
- `dimension` (required)
- `max_deviation` (required)
- `seed` (optional)
- `drop_rate` (optional)

**Proposed API (3 required, 0 optional):**
- `dimension` (required): `"frequency"` | `"duration"` | `"amplitude"`
- `max_drop_pct` (required): the maximum percentage each drop can reduce a tone by (1-100). E.g., 50 = up to 50% reduction.
- `drop_frequency_pct` (required): what percentage of tones get dropped (1-100). E.g., 40 = about 40% of tones are affected.

`max_drop_pct` and `drop_frequency_pct` control different musical ideas:
1. `max_drop_pct`: how severe each drop is
2. `drop_frequency_pct`: how often drops occur

Keeping them separate lets users combine them (e.g., frequent shallow drops, or rare deep drops).

**Removed:**
- `seed` — removed entirely, use fixed internal seed for deterministic behavior
- `max_deviation` — renamed to `max_drop_pct` (1-100 scale)
- `drop_rate` — renamed to `drop_frequency_pct` (1-100 scale)

---

### `ridged_drop` - REMOVE

**Decision:** Remove `ridged_drop` entirely. It doesn't clearly justify its existence alongside `random_drop` and `terraced_drift`. Its unique contribution (smooth periodic dips) is not well thought out and the API is hard to make intuitive.

**Future:** Revisit the concept later as a `terraced_drop` transform — designed from scratch with a clear purpose: structured, staircase-shaped drops across phrases and tone dimensions. This should be a separate feature designed intentionally rather than retrofitting the current ridged_drop.

---

### `add_pedal_point` → Rename to `add_pedal_tone` - Currently 5 Parameters

**Current API:**
- `frequency` (required)
- `duration` (required)
- `amplitude` (optional)
- `mode` (optional)
- `pulse_duration` (optional)

**Proposed API (1 required, 0 optional):**
- `frequency` (required): The pedal tone frequency in Hz

**Removed:**
- `duration` — derived automatically from the length of the musical context it's being applied to (phrase or score)
- `amplitude` — use sensible internal default
- `mode` — removed (sustain by default; if repeat/pulse is needed, revisit later)
- `pulse_duration` — removed along with mode

**Rename:** `add_pedal_point` → `add_pedal_tone` (more literal and clear)

---

### `accelerando` / `ritardando` - Currently 3 Parameters

**Current API:**
- `strength` (required)
- `jaggedness` (optional)
- `seed` (optional)

**Proposed API (1 required, 1 optional):**
- `strength` (required): `"subtle"` | `"moderate"` | `"dramatic"` (or numeric 0.0-1.0)
- `jaggedness` (optional): `"none"` | `"light"` | `"moderate"` | `"heavy"` (or numeric 0.0-1.0)

Both parameters are musically meaningful and well-named. `strength` controls how much the tempo changes. `jaggedness` adds stochastic roughness to the curve. Keep both.

**Removed:**
- `seed` — removed from public API, fixed internal seed used for deterministic behavior

---

## Summary: Before and After

| Transform | Before | After |
|-----------|--------|-------|
| `weierstrass` | 6 params | 2 params |
| `cellular_automata` | 5 params | 3 params |
| `terraced_drift` | 5 params | 2 params |
| `random_drop` | 4 params | 3 params |
| `ridged_drop` | 4 params | REMOVE |
| `add_pedal_point` | 5 params | 1 param (rename to `add_pedal_tone`) |
| `accelerando` | 3 params | 2 params |
| `ritardando` | 3 params | 2 params |

---

## Implementation Checkpoints

Each checkpoint is a small, self-contained change. Stop after each one, run the specified tests, and verify before continuing. Do not combine checkpoints.

---

### Phase 1: Simplify `weierstrass`

#### 1.1 Add intensity presets and resolver

Scope:
1. In `transforms/complexity/weierstrass.py`, add the preset mapping dict:
   ```python
   _WEIERSTRASS_INTENSITY_PRESETS = {
       "low": {"max_deviation": 0.05, "amplitude_scaling": 0.3, "ripples_per_wave": 2.0, "iterations": 6},
       "medium": {"max_deviation": 0.15, "amplitude_scaling": 0.5, "ripples_per_wave": 3.0, "iterations": 10},
       "high": {"max_deviation": 0.25, "amplitude_scaling": 0.6, "ripples_per_wave": 4.0, "iterations": 12},
       "extreme": {"max_deviation": 0.4, "amplitude_scaling": 0.8, "ripples_per_wave": 6.0, "iterations": 18},
   }
   ```
2. Add a `_resolve_intensity(value)` function that accepts `"low"`, `"medium"`, `"high"`, or `"extreme"` and returns the preset dict. Reject non-string values and unknown strings.
3. Add tests for the resolver.

Verification: `pytest tests/test_complexity_transforms.py`

---

#### 1.2 Refactor weierstrass function signature

Scope:
1. Change `apply_weierstrass_transform` to accept `dimension` and `intensity` only.
2. Remove `max_deviation`, `seed`, `amplitude_scaling`, `ripples_per_wave`, `iterations` from the public signature.
3. Internally resolve `intensity` to the preset values and pass them to `_WeierstrassProfile`.
4. Use a fixed internal seed (42).

Verification: `pytest tests/test_complexity_transforms.py`

---

#### 1.3 Update weierstrass params spec

Scope:
1. Update `WEIERSTRASS_PARAMS_SPEC` to expose only `dimension` (required) and `intensity` (required, enum: `"low"`, `"medium"`, `"high"`, `"extreme"`).
2. Remove all other fields from the spec.

Verification: `pytest tests/test_complexity_transforms.py tests/test_json_parser.py`

---

#### 1.4 Update weierstrass tests and demos

Scope:
1. Update all test calls to use the new 2-param API.
2. Update any composition JSON files that use `weierstrass` to the new API.
3. Remove tests that depend on removed public parameters.

Verification: `pytest tests/test_complexity_transforms.py tests/test_json_parser.py`

---

### Phase 2: Simplify `cellular_automata`

#### 2.1 Rewrite cellular automata implementation

This is the most complex change. The entire internal logic changes — the CA no longer uses random initial state. Instead, the initial state is derived from the input tones.

Scope:

1. In `transforms/complexity/cellular_automata.py`, remove `import random`.

2. Remove the existing `_CellularAutomataProfile` class entirely.

3. Add a new function `_derive_initial_state(tones, dimension)` in the same file (`transforms/complexity/cellular_automata.py`) that:
   - Takes the tone sequence and a resolved `ToneDimension`.
   - Extracts the target dimension value from each tone:
     - If `dimension == ToneDimension.FREQUENCY`: use `tone.frequency`
     - If `dimension == ToneDimension.DURATION`: use `tone.duration`
     - If `dimension == ToneDimension.AMPLITUDE`: use `tone.amplitude`
   - Computes the median of those values (use `sorted(values)[len(values) // 2]` — no need to import statistics).
   - Returns a binary list: `[1 if v >= median else 0 for v in values]`.
   - Edge case: if all values are identical (min == max), return alternating `[1, 0, 1, 0, ...]` of the same length.

4. Add a new function `_evolve_state(state, rule, generations)` that:
   - Takes the binary state, a rule number, and number of generations.
   - Calls `_get_next_cellular_state(state, rule)` in a loop `generations` times.
   - Returns the final evolved state.

5. Keep the existing `_get_next_cellular_state` function unchanged — it already works correctly.

6. Rewrite `apply_cellular_automata_transform` to:
   ```python
   def apply_cellular_automata_transform(
       tones: ToneSequence,
       dimension: ToneDimension | str,
       rule: int,
       max_deviation: float,
   ) -> ToneSequence:
       if not tones:
           return []
       if len(tones) == 1:
           return list(tones)

       from transforms.base import parse_dimension
       resolved_dimension = parse_dimension(dimension)

       initial_state = _derive_initial_state(tones, resolved_dimension)
       final_state = _evolve_state(initial_state, rule, generations=5)

       profile = [-1.0 if cell == 0 else 1.0 for cell in final_state]

       from transforms.complexity._modulation import _modulate_tone_dimension
       return _modulate_tone_dimension(tones, profile, resolved_dimension, max_deviation)
   ```

   Note: This bypasses the `apply_profile` helper and calls `_modulate_tone_dimension` directly. This is intentional — the old profile-based pattern doesn't fit because the CA now needs the tones themselves to derive its state, not just the length.

7. Remove the import of `apply_profile` from the file since it's no longer used.

Verification: `pytest tests/test_complexity_transforms.py` (tests will fail at this point because the function signature changed — that's expected, we'll fix tests in step 2.3).

---

#### 2.2 Update cellular automata params spec

Scope:
1. In the same file (`transforms/complexity/cellular_automata.py`), update `CELLULAR_AUTOMATA_PARAMS_SPEC`:
   ```python
   CELLULAR_AUTOMATA_PARAMS_SPEC = TransformParamsSpec(
       fields={
           "dimension": TransformParamFieldSpec(
               required=True,
               schema=EnumParam(allowed_values=tuple(ToneDimension)),
           ),
           "rule": TransformParamFieldSpec(
               required=True,
               schema=IntegerParam(),
           ),
           "max_deviation": TransformParamFieldSpec(
               required=True,
               schema=FloatParam(),
           ),
       }
   )
   ```
2. Remove `seed` and `width` fields.
3. Make `rule` required (it was previously optional).

Verification: `pytest tests/test_json_parser.py` (may still fail due to test updates needed).

---

#### 2.3 Update cellular automata tests and demos

Scope:
1. In `tests/test_complexity_transforms.py`, rewrite all cellular automata test calls to use the new 3-param signature: `dimension`, `rule`, `max_deviation`. Remove `seed` and `width` from all calls.
2. Remove or rewrite the "repeatability" test (it previously tested that same seed = same output; now same tones + same rule = same output).
3. Add new tests:
   - Same input tones + same rule → identical output (deterministic).
   - Different input tones + same rule → different output (SDIC).
   - Different rules + same tones → different output.
   - Empty input → returns empty list.
   - Single tone → returns the tone unchanged.
   - All tones with same frequency (uniform) → uses alternating fallback, still produces a valid result.
4. Update `compositions/score_cellular_automata_demo.json` to remove `seed` and ensure `rule` is present in all cellular automata transform entries.
5. Update `compositions/geological_example.json` if it uses cellular automata — remove `seed`, ensure `rule` is present.

Verification: `pytest tests/test_complexity_transforms.py tests/test_json_parser.py`

---

### Phase 3: Simplify `random_drop`

#### 3.1 Refactor random_drop function signature

Scope:
1. Change `apply_random_drop_transform` to accept `tones`, `dimension`, `max_drop_pct`, and `drop_frequency_pct`.
2. Remove `seed`, `max_deviation`, and `drop_rate` from the public signature.
3. Internally:
   - Convert `max_drop_pct` to internal max_deviation: `max_deviation = max_drop_pct / 100.0`
   - Convert `drop_frequency_pct` to internal drop_rate: `drop_rate = drop_frequency_pct / 100.0`
   - Use fixed internal seed (42).
4. Validate that `max_drop_pct` is between 1 and 100.
5. Validate that `drop_frequency_pct` is between 1 and 100.

Verification: `pytest tests/test_complexity_transforms.py`

---

#### 3.2 Update random_drop params spec

Scope:
1. Update `RANDOM_DROP_PARAMS_SPEC` to expose only `dimension` (required), `max_drop_pct` (required, float/int), and `drop_frequency_pct` (required, float/int).
2. Remove `seed`, `max_deviation`, and `drop_rate` fields.

Verification: `pytest tests/test_complexity_transforms.py tests/test_json_parser.py`

---

#### 3.3 Update random_drop tests and demos

Scope:
1. Rewrite tests to use the new 3-param API (`max_drop_pct`, `drop_frequency_pct`).
2. Update composition JSON files that use `random_drop`.

Verification: `pytest tests/test_complexity_transforms.py tests/test_json_parser.py`

---

### Phase 4: Simplify `terraced_drift`

#### 4.1 Refactor terraced_drift function signature

Scope:
1. Change `apply_terraced_drift_transform` to accept `tones`, `dimension`, and `max_step_change_pct`.
2. Remove `seed`, `max_deviation`, `step_size`, and `quantize_resolution` from the public signature.
3. Internally:
   - Convert `max_step_change_pct` to internal values: `step_size = max_step_change_pct / 100.0`
   - Set `max_deviation = step_size` (they're the same).
   - Set `quantize_resolution = step_size` (derived from step_size).
   - Use fixed internal seed (42).
4. Validate that `max_step_change_pct` is between 1 and 100.

Verification: `pytest tests/test_geological_modulation.py`

---

#### 4.2 Update terraced_drift params spec

Scope:
1. Update `TERRACED_DRIFT_PARAMS_SPEC` to expose only `dimension` (required) and `max_step_change_pct` (required, float/int).
2. Remove `seed`, `max_deviation`, `step_size`, and `quantize_resolution` fields.

Verification: `pytest tests/test_geological_modulation.py tests/test_json_parser.py`

---

#### 4.3 Update terraced_drift tests and demos

Scope:
1. Rewrite tests to use the new 2-param API (`dimension`, `max_step_change_pct`).
2. Update composition JSON files that use `terraced_drift`.

Verification: `pytest tests/test_geological_modulation.py tests/test_json_parser.py`

---

### Phase 5: Remove `ridged_drop`

#### 5.1 Remove ridged_drop from registry

Scope:
1. In `transforms/registry.py`, remove the import and registration of `ridged_drop` and `score_ridged_drop`.
2. Do NOT delete the implementation file yet.

Verification: `pytest tests/test_json_parser.py`

---

#### 5.2 Remove ridged_drop tests

Scope:
1. Remove all tests that directly test `ridged_drop` or `score_ridged_drop`.
2. Remove or update any integration tests that use `ridged_drop` (e.g., `test_geological_example_composition.py`).

Verification: `pytest tests/`

---

#### 5.3 Remove ridged_drop implementation files

Scope:
1. Delete `transforms/geological/ridged_drop.py`.
2. Remove any imports of ridged_drop from `transforms/geological/__init__.py` if present.
3. Update `compositions/geological_example.json` to remove the `ridged_drop` transform entry.
4. Remove `compositions/score_ridged_drop_demo.json` if it exists.

Verification: `pytest tests/`

---

### Phase 6: Simplify `accelerando` / `ritardando`

#### 6.1 Remove seed from accelerando/ritardando

Scope:
1. In `transforms/tempo/accelerando.py`, remove `seed` from the function signature.
2. Replace `random_source = random.Random(seed) if seed is not None else None` with `random_source = random.Random(42)`.
3. Do the same in `transforms/tempo/ritardando.py`.
4. Update `build_tempo_change_params_spec()` in `transforms/tempo/_common.py` to remove the `seed` field.

Verification: `pytest tests/test_tempo.py`

---

#### 6.2 Update accelerando/ritardando tests and demos

Scope:
1. Remove `seed` from all test calls to accelerando/ritardando.
2. Update any composition JSON files that pass `seed` to these transforms.

Verification: `pytest tests/test_tempo.py tests/test_json_parser.py`

---

### Phase 7: Rename `add_pedal_point` to `add_pedal_tone`

#### 7.1 Refactor add_pedal_point function signature

Scope:
1. In `transforms/counterpoint/fugue.py`, rename the function `add_pedal_point` to `add_pedal_tone`.
2. Change the signature to accept only `score: Score` and `frequency: float`.
3. Remove `duration`, `amplitude`, `mode`, and `pulse_duration` from the signature.
4. Internally, compute the duration from the score by finding the longest voice:
   ```python
   def add_pedal_tone(score: Score, frequency: float) -> Score:
       if frequency <= 0:
           raise ValueError("Pedal tone frequency must be greater than 0.")

       # Compute duration from the longest voice in the score
       duration = 0.0
       for voice in score.voices:
           voice_duration = sum(tone.duration for tone in voice.tones)
           duration = max(duration, voice_duration)

       if duration <= 0:
           duration = 1.0  # Fallback if score is empty

       amplitude = 0.5  # Fixed sensible default
       pedal_tones = [Tone(frequency=frequency, duration=duration, amplitude=amplitude)]
       return Score(score.voices + [Voice(pedal_tones)])
   ```
5. Remove the `_build_repeated_pedal_tones` helper function (no longer needed since "repeat" mode is removed).
6. Remove the import of `validate_add_pedal_point_params` at the top of the file.

Verification: `pytest tests/test_counterpoint_fugue.py` (tests will fail — expected, we'll fix them in 7.3).

---

#### 7.2 Update params spec and registry

Scope:
1. In `transforms/counterpoint/fugue.py`, replace `ADD_PEDAL_POINT_PARAMS_SPEC` with:
   ```python
   ADD_PEDAL_TONE_PARAMS_SPEC = TransformParamsSpec(
       fields={
           "frequency": TransformParamFieldSpec(
               schema=FloatParam(),
               required=True,
           ),
       }
   )
   ```
   Remove the `validator=validate_add_pedal_point_params` argument (no cross-parameter validation needed).
2. In `transforms/registry.py`:
   - Update the import to use `ADD_PEDAL_TONE_PARAMS_SPEC` and `add_pedal_tone` (instead of the old names).
   - Change the registration key from `"add_pedal_point"` to `"add_pedal_tone"`.
   - Update the `ScoreTransform` to reference the renamed function and spec.
3. In `composition/transform_params_validation.py`, delete the `validate_add_pedal_point_params` function entirely (it validated pulse_duration which no longer exists).

Verification: `pytest tests/test_counterpoint_fugue.py tests/test_json_parser.py` (tests will fail — expected).

---

#### 7.3 Update add_pedal_tone tests and demos

Scope:
1. In `tests/test_counterpoint_fugue.py`:
   - Rename all references from `add_pedal_point` to `add_pedal_tone`.
   - Update all test calls to use only `frequency` (remove `duration`, `amplitude`, `mode`, `pulse_duration`).
   - Remove tests for "repeat" mode and pulse_duration.
   - Remove tests for the `duration <= 0` validation (duration is now derived internally).
   - Add a test verifying that the pedal tone duration matches the longest voice in the score.
2. In `tests/test_json_parser.py`:
   - Update all references from `"add_pedal_point"` to `"add_pedal_tone"`.
   - Update test JSON payloads to only include `frequency` in params.
   - Remove tests for pulse_duration validation.
3. Update any composition JSON files that use `"add_pedal_point"`:
   - Change `"name": "add_pedal_point"` to `"name": "add_pedal_tone"`.
   - Remove `duration`, `amplitude`, `mode`, and `pulse_duration` from the params object.
   - Keep only `"frequency"` in params.

Verification: `pytest tests/test_counterpoint_fugue.py tests/test_json_parser.py`

---

### Phase 8: Documentation and Demos

#### 8.1 Update README

Scope:
1. Update the transforms documentation in `README.md` to reflect all new APIs.
2. Remove references to `ridged_drop`.
3. Update `add_pedal_point` references to `add_pedal_tone`.

Verification: Manual review.

---

#### 8.2 Final test pass

Scope:
1. Run the full test suite: `pytest tests/`
2. Fix any remaining failures.
3. Verify score-level transform variants still work: `score_cellular_automata`, `score_terraced_drift`, `score_random_drop`, and `score_weierstrass` should all accept the new param names and produce valid output.
4. Check for dead imports or unused code left behind from the refactor (e.g., `apply_profile` import in cellular_automata, any ridged_drop references).
5. Run all demo compositions to verify they produce output:
   ```shell
   for file in compositions/*_demo.json; do name="$(basename "$file" .json)"; python main.py --composition-file "$file" --output-name "$name"; done
   ```

Verification: All tests pass, all demos produce output.

---

## Open Questions

1. **Global randomness**: Should we add a composition-level setting for transforms that use stochastic processes internally (e.g., terraced_drift, random_drop)?

---

## References

- `features/done/simplify_ridged_drop_transform.md` - Previous work on `ridged_drop` (transform being removed)
- `transforms/geological/ridged_drop.py` - Current implementation (to be removed)
