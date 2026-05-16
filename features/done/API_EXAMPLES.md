# Public API Examples: Before & After Simplification

## Overview
This document shows concrete examples of how the public API will look after simplifying the transforms.

---

## 1. weierstrass Transform

### BEFORE (6 parameters)
```python
# Very complex - users need to understand algorithm internals
transform.weierstrass(
    dimension="frequency",
    max_deviation=0.15,
    seed=42,  # Implementation detail
    amplitude_scaling=0.5,  # Technical parameter
    ripples_per_wave=3.0,  # Technical parameter
    iterations=10  # Technical parameter
)
```

### AFTER (2 parameters)
```python
# Simple - users describe musical intent with presets
transform.weierstrass(
    dimension="frequency",
    intensity="medium"  # Musically intuitive preset
)

# All preset variants:
transform.weierstrass(dimension="frequency", intensity="low")
transform.weierstrass(dimension="frequency", intensity="medium")
transform.weierstrass(dimension="frequency", intensity="high")
transform.weierstrass(dimension="frequency", intensity="extreme")

# Works for all dimensions:
transform.weierstrass(dimension="duration", intensity="medium")
transform.weierstrass(dimension="amplitude", intensity="low")
```

**Internal mapping:**
- `"low"` → `max_deviation=0.05, amplitude_scaling=0.3, ripples_per_wave=2.0, iterations=6`
- `"medium"` → `max_deviation=0.15, amplitude_scaling=0.5, ripples_per_wave=3.0, iterations=10`
- `"high"` → `max_deviation=0.25, amplitude_scaling=0.6, ripples_per_wave=4.0, iterations=12`
- `"extreme"` → `max_deviation=0.4, amplitude_scaling=0.8, ripples_per_wave=6.0, iterations=18`

---

## 2. cellular_automata Transform

### BEFORE (5 parameters)
```python
# Conceptually wrong: using RNG for initial state defeats the purpose of CA
transform.cellular_automata(
    dimension="duration",
    max_deviation=0.3,
    rule=110,
    seed=42,  # Generates random initial state — wrong! CA is deterministic
    width=31  # Artificial width unrelated to input
)
```

### AFTER (4 parameters)
```python
# The rule IS the transform. Initial state derived from the input tones themselves.
transform.cellular_automata(
    dimension="duration",
    rule=30,
    max_deviation=0.3,
    generations=5
)

# Classic Wolfram rules:
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.2, generations=5)   # Chaotic
transform.cellular_automata(dimension="frequency", rule=110, max_deviation=0.2, generations=5)  # Complex/ordered
transform.cellular_automata(dimension="frequency", rule=90, max_deviation=0.2, generations=5)   # Fractal/self-similar

# generations controls how far the pattern diverges from the input's original structure:
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.3, generations=1)   # Minimal evolution
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.3, generations=10)  # Deep evolution

# Works for all dimensions:
transform.cellular_automata(dimension="duration", rule=30, max_deviation=0.3, generations=5)
transform.cellular_automata(dimension="amplitude", rule=110, max_deviation=0.4, generations=8)

# max_deviation controls how strongly the CA pattern modulates the tones:
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.1, generations=5)  # Subtle effect
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.5, generations=5)  # Dramatic effect
```

**How it works internally:**

1. Extract target dimension values from input tones (e.g., all frequencies)
2. Compute median, threshold into binary: `>= median → 1, < median → 0`
3. This binary row (one cell per tone) is the CA's initial state
4. Evolve the state using the rule for a fixed number of generations
5. Read the final evolved state — maps 1:1 back to tones as modulation (scaled by `max_deviation`)

The music's own structure is the initial condition. The rule deterministically reshapes it. This is true to the mathematical concept: cellular automata exhibit sensitivity to initial conditions (SDIC) — the input pattern matters, not a random starting point.

**Note:** `seed` and `width` are removed entirely — both from public API and internal implementation. There is no randomness. The initial state comes from the input tones, the width is simply the number of tones, and `generations` controls how far the state evolves.

---

## 3. terraced_drift Transform

### BEFORE (5 parameters)
```python
# Complex parameters that require experimentation
transform.terraced_drift(
    dimension="frequency",
    max_deviation=0.25,
    seed=42,  # Implementation detail
    step_size=0.25,  # Useful but unclear scale
    quantize_resolution=0.2  # Confusing, closely related to step_size
)
```

### AFTER (2 parameters)
```python
# max_step_change_pct: how much each tone can change from the previous (1-100)
transform.terraced_drift(
    dimension="frequency",
    max_step_change_pct=25  # Each tone can change by up to 25% from the previous
)

# Fine, subtle terracing:
transform.terraced_drift(dimension="frequency", max_step_change_pct=10)

# Wide, dramatic staircase:
transform.terraced_drift(dimension="frequency", max_step_change_pct=50)

# Works for all dimensions:
transform.terraced_drift(dimension="duration", max_step_change_pct=15)
transform.terraced_drift(dimension="amplitude", max_step_change_pct=30)
```

**Removed:**
- `seed` — removed, fixed internal seed for deterministic behavior
- `max_deviation` — derived internally from `max_step_change_pct`
- `step_size` — replaced by `max_step_change_pct` (same concept, clearer name and 1-100 scale)
- `quantize_resolution` — derived internally from `max_step_change_pct`

---

## 4. random_drop Transform

### BEFORE (4 parameters)
```python
# Users manually tune both deviation and drop rate with unclear scales
transform.random_drop(
    dimension="frequency",
    max_deviation=0.5,  # Unclear what 0.5 means
    seed=42,  # Implementation detail
    drop_rate=0.4  # Unclear scale
)
```

### AFTER (3 parameters)
```python
# max_drop_pct: how severe each drop is (1-100)
# drop_frequency_pct: how often drops occur (1-100)
transform.random_drop(
    dimension="frequency",
    max_drop_pct=50,           # Each drop reduces the value by up to 50%
    drop_frequency_pct=40      # About 40% of tones get dropped
)

# Frequent shallow drops:
transform.random_drop(dimension="frequency", max_drop_pct=10, drop_frequency_pct=60)

# Rare deep drops:
transform.random_drop(dimension="frequency", max_drop_pct=75, drop_frequency_pct=15)

# Works for all dimensions:
transform.random_drop(dimension="duration", max_drop_pct=30, drop_frequency_pct=20)
transform.random_drop(dimension="amplitude", max_drop_pct=50, drop_frequency_pct=50)
```

**Removed:**
- `seed` — removed, fixed internal seed for deterministic behavior
- `max_deviation` — renamed to `max_drop_pct` (1-100 scale)
- `drop_rate` — renamed to `drop_frequency_pct` (1-100 scale)

---

## 5. ridged_drop Transform — REMOVE

**Decision:** Remove `ridged_drop` entirely. It doesn't clearly justify its existence alongside `random_drop` and `terraced_drift`. Its unique contribution (smooth periodic dips) is not well thought out and the API is hard to make intuitive.

**Future:** Revisit the concept later as a `terraced_drop` transform — designed from scratch with a clear purpose: structured, staircase-shaped drops across phrases and tone dimensions.

---

## 6. add_pedal_tone Transform (renamed from add_pedal_point)

### BEFORE (5 parameters)
```python
# Requires tuning every aspect, duration is redundant
transform.add_pedal_point(
    frequency=110.0,  # Hz
    duration=8.0,  # beats — should just match the phrase length
    amplitude=0.6,  # Often just uses default
    mode="sustain",  # Two modes with different params
    pulse_duration=0.5  # Only used in "pulse" mode
)
```

### AFTER (1 parameter)
```python
# Just specify the pedal tone frequency — duration matches the phrase automatically
transform.add_pedal_tone(frequency=110.0)

# Different pedal tones:
transform.add_pedal_tone(frequency=55.0)    # Low A
transform.add_pedal_tone(frequency=130.81)  # Low C
transform.add_pedal_tone(frequency=220.0)   # A below middle C
```

**Removed:**
- `duration` — derived automatically from the length of the musical context (phrase or score)
- `amplitude` — sensible internal default
- `mode` — removed (sustain by default)
- `pulse_duration` — removed along with mode

**Renamed:** `add_pedal_point` → `add_pedal_tone`

---

## 7. accelerando / ritardando Transforms

### BEFORE (3 parameters)
```python
# seed is an implementation detail that shouldn't be exposed as a raw number
transform.accelerando(
    strength=0.5,  # How much to accelerate
    jaggedness=0.3,  # Optional texture parameter
    seed=42  # Implementation detail
)
```

### AFTER (2 parameters)
```python
# strength and jaggedness are musically meaningful — keep them
transform.accelerando(
    strength="moderate",   # How much the tempo accelerates
    jaggedness="light"     # How rough/stochastic the curve is
)

# Strength variants:
transform.accelerando(strength="subtle")
transform.accelerando(strength="moderate")
transform.accelerando(strength="dramatic")

# Jaggedness variants:
transform.accelerando(strength="moderate", jaggedness="none")    # Smooth curve
transform.accelerando(strength="moderate", jaggedness="light")   # Slight roughness
transform.accelerando(strength="moderate", jaggedness="heavy")   # Very rough

# Same for ritardando:
transform.ritardando(strength="moderate", jaggedness="light")
transform.ritardando(strength="dramatic", jaggedness="none")

# Numeric values also accepted:
transform.accelerando(strength=0.7, jaggedness=0.2)
```

**Removed:**
- `seed` — removed from public API, fixed internal seed used for deterministic behavior

---

## Summary: API Complexity Reduction

| Transform | Before | After | Reduction |
|-----------|--------|-------|-----------|
| `weierstrass` | 6 params | 2 params | 67% reduction |
| `cellular_automata` | 5 params | 4 params | 20% reduction |
| `terraced_drift` | 5 params | 2 params | 60% reduction |
| `random_drop` | 4 params | 3 params | 25% reduction |
| `ridged_drop` | 4 params | REMOVE | — |
| `add_pedal_point` | 5 params | 1 param (rename to `add_pedal_tone`) | 80% reduction |
| `accelerando` | 3 params | 2 params | 33% reduction |
| `ritardando` | 3 params | 2 params | 33% reduction |

---

## Design Philosophy Examples

### Good: Intent-based Parameters
```python
# Users describe what they want musically
transform.weierstrass(dimension="frequency", intensity="low")
transform.cellular_automata(dimension="duration", rule=30, max_deviation=0.3, generations=5)
transform.random_drop(dimension="amplitude", max_drop_pct=50, drop_frequency_pct=40)
```

### Bad: Implementation-detail Parameters
```python
# Users have to understand how the algorithm works
transform.weierstrass(
    dimension="frequency", 
    max_deviation=0.15, 
    amplitude_scaling=0.5, 
    ripples_per_wave=3.0, 
    iterations=10, 
    seed=42
)
```

---

## Flexibility vs Complexity Balance

### Flexible AND Simple
```python
# Different dimensions allow creative applications
transform.weierstrass(dimension="frequency", intensity="medium")  # Main use case
transform.weierstrass(dimension="duration", intensity="medium")    # Rhythmic variation
transform.weierstrass(dimension="amplitude", intensity="medium")   # Dynamic texture
```

### Too Complex
```python
# Users can tune everything but often don't need to
transform.weierstrass(
    dimension="frequency",
    max_deviation=0.15,
    amplitude_scaling=0.5,
    ripples_per_wave=3.0,
    iterations=10
)
```
