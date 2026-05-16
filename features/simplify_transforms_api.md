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
1. Update `WEIERSTRASS_PARAMS_SPEC` to expose only `dimension` (required) and `intensity` (required, enum: `"very_low"`, `"low"`, `"medium"`, `"high"`, `"extreme"`).
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

#### 2.1 Rewrite cellular automata to derive initial state from input tones

Scope:
1. In `transforms/complexity/cellular_automata.py`, remove `import random`.
2. Rewrite `_CellularAutomataProfile` to accept `tones` (the input tone sequence), `dimension`, and `rule`.
3. The `generate` method should:
   - Extract the target dimension values from each tone.
   - Compute the median.
   - Threshold into binary: `>= median → 1, < median → 0`.
   - If all values are the same (uniform), use alternating `[1, 0, 1, 0...]` as fallback.
   - Evolve the binary state for a fixed number of generations (use 5).
   - Return the final state mapped to -1.0 / 1.0 values.
4. For single tone input, return `[0.0]` (no modulation).

Verification: `pytest tests/test_complexity_transforms.py`

---

#### 2.2 Refactor cellular automata function signature

Scope:
1. Change `apply_cellular_automata_transform` to accept `tones`, `dimension`, `rule`, and `max_deviation`.
2. Remove `seed` and `width` from the signature.
3. Pass tones and dimension into the profile so it can derive the initial state.
4. Make `rule` required (no default), `max_deviation` required (no default).

Note: The `_modulation.py` helper interface may need updating since the profile now needs access to tones and dimension to derive initial state. The profile's `generate` method currently only takes `length`. Refactor as needed — the profile can receive the tones at construction time and `generate` can still take `length` for interface compatibility.

Verification: `pytest tests/test_complexity_transforms.py`

---

#### 2.3 Update cellular automata params spec

Scope:
1. Update `CELLULAR_AUTOMATA_PARAMS_SPEC` to expose only `dimension` (required), `rule` (required, integer), and `max_deviation` (required, float).
2. Remove `seed` and `width` fields.

Verification: `pytest tests/test_complexity_transforms.py tests/test_json_parser.py`

---

#### 2.4 Update cellular automata tests and demos

Scope:
1. Rewrite tests to use the new 3-param API.
2. Tests should verify:
   - Different input tones produce different modulation patterns (SDIC).
   - Same input tones + same rule produce identical results (deterministic).
   - Different rules produce different results.
   - Empty input returns empty list.
   - Single tone returns unchanged.
   - Uniform dimension values (all same frequency) use alternating fallback.
3. Update composition JSON files that use `cellular_automata`.

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
1. In `transforms/counterpoint/fugue.py`, rename `add_pedal_point` to `add_pedal_tone`.
2. Change the signature to accept only `score` and `frequency`.
3. Internally, compute duration from the score: sum the durations of the longest voice.
4. Use a fixed amplitude default (e.g., 0.5).
5. Always use "sustain" mode.
6. Remove `duration`, `amplitude`, `mode`, and `pulse_duration` from the signature.

Verification: `pytest tests/test_counterpoint_fugue.py`

---

#### 7.2 Update params spec and registry

Scope:
1. Update `ADD_PEDAL_POINT_PARAMS_SPEC` to expose only `frequency` (required).
2. Rename it to `ADD_PEDAL_TONE_PARAMS_SPEC`.
3. In `transforms/registry.py`, update the registration to use the new name `add_pedal_tone` and the renamed function/spec.
4. Remove the cross-parameter validation in `composition/transform_params_validation.py` (pulse_duration requirement is gone).

Verification: `pytest tests/test_counterpoint_fugue.py tests/test_json_parser.py`

---

#### 7.3 Update add_pedal_tone tests and demos

Scope:
1. Update all tests to use the new 1-param API and the new name `add_pedal_tone`.
2. Update composition JSON files that use `add_pedal_point` to use `add_pedal_tone` with only `frequency`.

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
3. Run all demo compositions to verify they produce output:
   ```shell
   for file in compositions/*_demo.json; do name="$(basename "$file" .json)"; python main.py --composition-file "$file" --output-name "$name"; done
   ```

Verification: All tests pass, all demos produce output.

---

## Open Questions

1. **Weierstrass intensity presets**: Should we revisit the `intensity` preset approach for weierstrass (same vagueness issue we identified in other transforms), or is it acceptable there?

2. **Global randomness**: Should we add a composition-level setting for transforms that use stochastic processes internally (e.g., terraced_drift, random_drop)?

---

## References

- `features/done/simplify_ridged_drop_transform.md` - Previous work on `ridged_drop` (transform being removed)
- `transforms/geological/ridged_drop.py` - Current implementation (to be removed)
