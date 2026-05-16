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
- `intensity` (required): `"subtle"` | `"medium"` | `"intense"`

The `intensity` preset controls both the deviation amount AND the texture characteristics. Users pick how much weierstrass wobble they want, and the preset handles all the internal tuning.

**Preset mapping:**
```python
_WEIERSTRASS_INTENSITY_PRESETS = {
    "subtle": {"max_deviation": 0.05, "amplitude_scaling": 0.3, "ripples_per_wave": 2.0, "iterations": 6},
    "medium": {"max_deviation": 0.15, "amplitude_scaling": 0.5, "ripples_per_wave": 3.0, "iterations": 10},
    "intense": {"max_deviation": 0.3, "amplitude_scaling": 0.7, "ripples_per_wave": 5.0, "iterations": 15},
}
```

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

### Phase 1: Simplify Complexity Transforms

1. Update `weierstrass` to 2-param API
2. Update `cellular_automata` to 3-param API (remove seed/width, derive initial state from input)
3. Update `random_drop` to 2-param API

### Phase 2: Simplify Geological Transforms

4. Update `terraced_drift` to 2-param API (remove seed, max_deviation, quantize_resolution; derive internally from step_size)
5. Remove `ridged_drop` entirely (revisit later as a `terraced_drop` designed from scratch)

### Phase 3: Simplify Other Transforms

6. Update `accelerando` / `ritardando` to 1-param API
7. Rename `add_pedal_point` to `add_pedal_tone`, reduce to 1-param API (frequency only, duration derived from context)

### Phase 4: Documentation and Demos

8. Update README with new APIs
9. Update all demo files
10. Final test pass

---

## Open Questions

1. **Numeric escape hatch**: Should we allow numeric values as alternatives to presets (e.g., `intensity: 0.7`)? This was done for `ridged_drop`'s `drop_depth`. Adds flexibility but also complexity.

2. **Preset vocabulary**: Should all transforms use the same preset names?
   - Option A: Consistent (`"subtle"` | `"medium"` | `"intense"` everywhere)
   - Option B: Context-specific (`"sparse"` | `"moderate"` | `"dense"` for drop-based transforms)

3. **Global randomness**: If we remove per-transform `new_pattern_each_use`, should we add a composition-level `randomize: true` setting that makes all stochastic transforms use random seeds?

---

## References

- `features/simplify_ridged_drop_transform.md` - Recent work on `ridged_drop` (may need partial revert)
- `transforms/geological/ridged_drop.py` - Current implementation with presets
