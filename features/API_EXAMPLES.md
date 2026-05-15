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
# Simple - users describe musical intent
transform.weierstrass(
    dimension="frequency",
    intensity="medium"  # Musically intuitive
)

# All preset variants:
transform.weierstrass(dimension="frequency", intensity="subtle")
transform.weierstrass(dimension="frequency", intensity="medium")
transform.weierstrass(dimension="frequency", intensity="intense")

# Works for all dimensions:
transform.weierstrass(dimension="duration", intensity="medium")
transform.weierstrass(dimension="amplitude", intensity="subtle")
```

**Internal mapping:**
- `"subtle"` → `max_deviation=0.05, amplitude_scaling=0.3, ripples_per_wave=2.0, iterations=6`
- `"medium"` → `max_deviation=0.15, amplitude_scaling=0.5, ripples_per_wave=3.0, iterations=10`
- `"intense"` → `max_deviation=0.3, amplitude_scaling=0.7, ripples_per_wave=5.0, iterations=15`

---

## 2. cellular_automata Transform

### BEFORE (5 parameters)
```python
# Users need to know cellular automata rules
transform.cellular_automata(
    dimension="duration",
    max_deviation=0.3,
    rule=110,  # Technical implementation detail
    seed=42,  # Implementation detail  
    width=31  # Technical parameter
)
```

### AFTER (2 parameters)
```python
# Describe the pattern you want, not the algorithm
transform.cellular_automata(
    dimension="duration",
    pattern="structured"  # Describes musical behavior
)

# All preset variants:
transform.cellular_automata(dimension="duration", pattern="chaotic")
transform.cellular_automata(dimension="duration", pattern="structured")
transform.cellular_automata(dimension="duration", pattern="fractal")

transform.cellular_automata(dimension="frequency", pattern="fractal")
transform.cellular_automata(dimension="amplitude", pattern="chaotic")
```

**Internal mapping:**
- `"chaotic"` → `rule=30, width=31, max_deviation=0.4`
- `"structured"` → `rule=110, width=31, max_deviation=0.3`
- `"fractal"` → `rule=90, width=31, max_deviation=0.35`

---

## 3. terraced_drift Transform

### BEFORE (5 parameters)
```python
# Complex parameters that require experimentation
transform.terraced_drift(
    dimension="frequency",
    max_deviation=0.25,
    seed=42,  # Implementation detail
    step_size=0.25,  # Technical parameter
    quantize_resolution=0.2  # Technical parameter
)
```

### AFTER (2 parameters)
```python
# Simple intent-based parameters
transform.terraced_drift(
    dimension="frequency",
    intensity="moderate"  # Describes musical effect
)

# All preset variants:
transform.terraced_drift(dimension="frequency", intensity="subtle")
transform.terraced_drift(dimension="frequency", intensity="moderate")
transform.terraced_drift(dimension="frequency", intensity="dramatic")

transform.terraced_drift(dimension="duration", intensity="subtle")
transform.terraced_drift(dimension="amplitude", intensity="dramatic")
```

**Internal mapping:**
- `"subtle"` → `max_deviation=0.1, step_size=0.1, quantize_resolution=0.1`
- `"moderate"` → `max_deviation=0.25, step_size=0.25, quantize_resolution=0.2`
- `"dramatic"` → `max_deviation=0.5, step_size=0.5, quantize_resolution=0.3`

---

## 4. random_drop Transform

### BEFORE (4 parameters)
```python
# Users manually tune both deviation and drop rate
transform.random_drop(
    dimension="frequency",
    max_deviation=0.5,
    seed=42,  # Implementation detail
    drop_rate=0.4  # Technical parameter
)
```

### AFTER (2 parameters)
```python
# Describe the drop density you want
transform.random_drop(
    dimension="frequency",
    intensity="moderate"  # Describes drop density
)

# All preset variants:
transform.random_drop(dimension="frequency", intensity="sparse")
transform.random_drop(dimension="frequency", intensity="moderate")
transform.random_drop(dimension="frequency", intensity="dense")

transform.random_drop(dimension="duration", intensity="sparse")
transform.random_drop(dimension="amplitude", intensity="dense")
```

**Internal mapping:**
- `"sparse"` → `max_deviation=0.3, drop_rate=0.2`
- `"moderate"` → `max_deviation=0.5, drop_rate=0.4`
- `"dense"` → `max_deviation=0.7, drop_rate=0.6`

---

## 5. ridged_drop Transform

### BEFORE (4 parameters)
```python
# Complex paramters that overlap in purpose
transform.ridged_drop(
    dimension="frequency",
    drop_depth=0.5,  # Related to intensity
    intensity=0.7,  # Overlaps with drop_depth
    new_pattern_each_use=True  # Implementation detail - randomness flag
)
```

### AFTER (2 parameters)
```python
# Single intensity parameter handles everything
transform.ridged_drop(
    dimension="frequency",
    intensity="medium"  # Combines drop_depth and ridge characteristics
)

# All preset variants:
transform.ridged_drop(dimension="frequency", intensity="subtle")
transform.ridged_drop(dimension="frequency", intensity="medium")
transform.ridged_drop(dimension="frequency", intensity="severe")

transform.ridged_drop(dimension="duration", intensity="subtle")
transform.ridged_drop(dimension="amplitude", intensity="severe")
```

**Internal mapping:**
- `"subtle"` → `drop_depth=0.25, octaves=2, ridge_density=0.2, drop_when_noise_above=0.7`
- `"medium"` → `drop_depth=0.5, octaves=3, ridge_density=0.3, drop_when_noise_above=0.5`
- `"severe"` → `drop_depth=0.75, octaves=4, ridge_density=0.45, drop_when_noise_above=0.3`

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
| `cellular_automata` | 5 params | 2 params | 60% reduction |
| `terraced_drift` | 5 params | 2 params | 60% reduction |
| `random_drop` | 4 params | 2 params | 50% reduction |
| `ridged_drop` | 4 params | 2 params | 50% reduction |
| `add_pedal_point` | 5 params | 2-3 params | 40-60% reduction |
| `accelerando` | 3 params | 1 param | 67% reduction |
| `ritardando` | 3 params | 1 param | 67% reduction |

---

## Design Philosophy Examples

### Good: Intent-based Parameters
```python
# Users describe what they want musically
transform.weierstrass(dimension="frequency", intensity="subtle")
transform.cellular_automata(dimension="duration", pattern="fractal")
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
