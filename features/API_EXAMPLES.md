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

### AFTER (2-3 parameters)
```python
# Simple - users describe musical intent with presets
transform.weierstrass(
    dimension="frequency",
    intensity="medium"  # Musically intuitive preset
)

# Optional override for fine control:
transform.weierstrass(
    dimension="frequency",
    intensity="medium",  # Preset for internal texture
    max_deviation=0.25   # Override the deviation amount
)

# All preset variants:
transform.weierstrass(dimension="frequency", intensity="subtle")
transform.weierstrass(dimension="frequency", intensity="medium")
transform.weierstrass(dimension="frequency", intensity="intense")

# Works for all dimensions:
transform.weierstrass(dimension="duration", intensity="medium")
transform.weierstrass(dimension="amplitude", intensity="subtle")

# Creative combinations with custom deviation:
transform.weierstrass(dimension="frequency", intensity="subtle", max_deviation=0.1)
transform.weierstrass(dimension="frequency", intensity="intense", max_deviation=0.5)
```

**Internal mapping:**
- `"subtle"` → `amplitude_scaling=0.3, ripples_per_wave=2.0, iterations=6`
- `"medium"` → `amplitude_scaling=0.5, ripples_per_wave=3.0, iterations=10`
- `"intense"` → `amplitude_scaling=0.7, ripples_per_wave=5.0, iterations=15`

**Note:** `max_deviation` is optional and can be specified to override the preset's deviation amount, giving users fine control without exposing internal algorithm parameters.

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

### AFTER (3 parameters)
```python
# The rule IS the transform. Initial state derived from the input tones themselves.
transform.cellular_automata(
    dimension="duration",
    rule=30,
    max_deviation=0.3
)

# Classic Wolfram rules:
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.2)   # Chaotic
transform.cellular_automata(dimension="frequency", rule=110, max_deviation=0.2)  # Complex/ordered
transform.cellular_automata(dimension="frequency", rule=90, max_deviation=0.2)   # Fractal/self-similar

# Works for all dimensions:
transform.cellular_automata(dimension="duration", rule=30, max_deviation=0.3)
transform.cellular_automata(dimension="amplitude", rule=110, max_deviation=0.4)

# max_deviation controls how strongly the CA pattern modulates the tones:
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.1)  # Subtle effect
transform.cellular_automata(dimension="frequency", rule=30, max_deviation=0.5)  # Dramatic effect
```

**How it works internally:**

1. Extract target dimension values from input tones (e.g., all frequencies)
2. Compute median, threshold into binary: `>= median → 1, < median → 0`
3. This binary row (one cell per tone) is the CA's initial state
4. Evolve the state using the rule for a fixed number of generations
5. Read the final evolved state — maps 1:1 back to tones as modulation (scaled by `max_deviation`)

The music's own structure is the initial condition. The rule deterministically reshapes it. This is true to the mathematical concept: cellular automata exhibit sensitivity to initial conditions (SDIC) — the input pattern matters, not a random starting point.

**Note:** `seed` and `width` are removed entirely — both from public API and internal implementation. There is no randomness. The initial state comes from the input tones, and the width is simply the number of tones.

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

## 5. ridged_drop Transform

### BEFORE (4 parameters)
```python
# drop_depth is unclear about scale, new_pattern_each_use is an implementation detail
transform.ridged_drop(
    dimension="frequency",
    drop_depth=0.5,  # Unclear what 0.5 means
    intensity="medium",  # Controls pattern density
    new_pattern_each_use=True  # Implementation detail - randomness flag
)
```

### AFTER (2-3 parameters)
```python
# max_drop_depth_pct: how far tones can drop, as a percentage (1-100)
# intensity: how active/dense the drop pattern is (optional, defaults to "medium")
transform.ridged_drop(
    dimension="frequency",
    max_drop_depth_pct=50  # Tones can drop by up to 50%
)

# With explicit intensity:
transform.ridged_drop(dimension="frequency", max_drop_depth_pct=50, intensity="subtle")
transform.ridged_drop(dimension="frequency", max_drop_depth_pct=50, intensity="medium")
transform.ridged_drop(dimension="frequency", max_drop_depth_pct=50, intensity="severe")

# Works for all dimensions:
transform.ridged_drop(dimension="duration", max_drop_depth_pct=25)
transform.ridged_drop(dimension="amplitude", max_drop_depth_pct=75, intensity="severe")

# Independent controls allow creative combinations:
transform.ridged_drop(dimension="frequency", max_drop_depth_pct=10, intensity="severe")  # Dense but shallow
transform.ridged_drop(dimension="frequency", max_drop_depth_pct=75, intensity="subtle")  # Sparse but deep
```

**Removed:**
- `new_pattern_each_use` — removed, per-transform randomness toggles eliminated
- `drop_depth` — renamed to `max_drop_depth_pct` (1-100 scale, "max" indicates it's a ceiling)

---

## 6. add_pedal_point Transform

### BEFORE (5 parameters)
```python
# Requires tuning every aspect
transform.add_pedal_point(
    frequency=110.0,  # Hz
    duration=8.0,  # beats
    amplitude=0.6,  # Often just uses default
    mode="sustain",  # Two modes with different params
    pulse_duration=0.5  # Only used in "pulse" mode
)
```

### AFTER (2-3 parameters)
```python
# Core parameters only - sensible defaults for the rest
transform.add_pedal_point(
    frequency=110.0,  # Hz - the pedal note
    duration=8.0  # beats - how long it lasts
)

# Optional mode parameter for different behaviors:
transform.add_pedal_point(
    frequency=110.0,
    duration=8.0,
    mode="sustain"  # Default behavior - no pulse_duration needed
)

transform.add_pedal_point(
    frequency=110.0,
    duration=8.0,
    mode="pulse"  # Will derive pulse_duration from context or use fixed ratio
)
```

**Internal defaults:**
- `amplitude` → defaults to `0.6` (sensible level that balances with other notes)
- `pulse_duration` in "pulse" mode → derived from beat structure or uses fixed ratio like 0.125 beats

---

## 7. accelerando / ritardando Transforms

### BEFORE (3 parameters)
```python
# Multiple ways to control the same thing
transform.accelerando(
    strength=0.5,  # How much to accelerate
    jaggedness=0.3,  # Optional texture parameter
    seed=42  # Implementation detail
)
```

### AFTER (1 parameter)
```python
# Single parameter describes the effect strength
transform.accelerando(
    strength="moderate"  # Describes how dramatic the accel is
)

# All preset variants (same for ritardando):
transform.accelerando(strength="subtle")
transform.accelerando(strength="moderate")
transform.accelerando(strength="dramatic")

transform.ritardando(strength="subtle")
transform.ritardando(strength="moderate") 
transform.ritardando(strength="dramatic")
```

**Rationale:**
- `jaggedness` removed - if users want jagged tempo changes, they can layer with other transforms like `weierstrass` or `cellular_automata`
- Single `strength` parameter with presets keeps the API clean and focused on musical intent

---

## Summary: API Complexity Reduction

| Transform | Before | After | Reduction |
|-----------|--------|-------|-----------|
| `weierstrass` | 6 params | 2 params | 67% reduction |
| `cellular_automata` | 5 params | 3 params | 40% reduction |
| `terraced_drift` | 5 params | 2 params | 60% reduction |
| `random_drop` | 4 params | 3 params | 25% reduction |
| `ridged_drop` | 4 params | 2-3 params | 25-50% reduction |
| `add_pedal_point` | 5 params | 2-3 params | 40-60% reduction |
| `accelerando` | 3 params | 1 param | 67% reduction |
| `ritardando` | 3 params | 1 param | 67% reduction |

---

## Design Philosophy Examples

### Good: Intent-based Parameters
```python
# Users describe what they want musically
transform.weierstrass(dimension="frequency", intensity="subtle")
transform.cellular_automata(dimension="duration", rule=30, max_deviation=0.3)
transform.random_drop(dimension="amplitude", intensity="dense")
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
