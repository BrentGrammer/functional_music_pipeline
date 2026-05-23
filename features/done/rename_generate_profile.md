# Rename and Simplify the \_GenerateProfile / Modulation Modules

## Problem

- `_GeneratedProfile` Protocol is duplicated identically in `transforms/geological/_modulation.py` and `transforms/complexity/_modulation.py`.
- `_modulate_tone_dimension` and `apply_profile` are also duplicated across both files.
- The Protocol + profile dataclass + `apply_profile` pattern adds indirection for no benefit: `apply_profile` does nothing except call `profile.generate(len(tones))` and pass the result to `_modulate_tone_dimension`.
- `cellular_automata.py` already bypasses the profile pattern entirely — it calls `_modulate_tone_dimension` directly with a plain `list[float]`. The other three transforms (terraced_drift, random_drop, weierstrass) should do the same.
- The name `_GeneratedProfile` is generic and doesn't describe what it actually is: a fluctuation/modulation value builder.

## Current consumers

| Transform | Module used | What it calls |
|---|---|---|
| `terraced_drift` | `geological/_modulation` | `apply_profile` (via `_TerracedBrownianProfile`) |
| `random_drop` | `complexity/_modulation` | `apply_profile` (via `_RandomDropProfile`) |
| `weierstrass` | `complexity/_modulation` | `apply_profile` (via `_WeierstrassProfile`) |
| `cellular_automata` | `complexity/_modulation` | `_modulate_tone_dimension` directly |

## Plan

### 1. Create `transforms/_modulation.py` — single shared module

Contains one function:

```python
def apply_fluctuations(
    tones: list[Tone],
    fluctuations: list[float],
    dimension: ToneDimension,
    max_deviation: float,
) -> list[Tone]:
```

Renamed from `_modulate_tone_dimension`. Takes a plain `list[float]` directly — no profile object, no Protocol.

### 2. Delete both duplicate `_modulation.py` files

- `transforms/geological/_modulation.py`
- `transforms/complexity/_modulation.py`

### 3. Update each transform

- **`cellular_automata.py`** — re-point import to `transforms._modulation`, rename call to `apply_fluctuations`.
- **`terraced_drift.py`** — remove `_TerracedBrownianProfile` dataclass, replace with `_build_terraced_fluctuations(length, step_size, quantize_resolution)` function. Call `apply_fluctuations` directly.
- **`random_drop.py`** — remove `_RandomDropProfile` dataclass, replace with `_build_random_drop_fluctuations(length, drop_rate)`. Call `apply_fluctuations` directly.
- **`weierstrass.py`** — remove `_WeierstrassProfile` dataclass, replace with `_build_weierstrass_fluctuations(length, amplitude_scaling, ripples_per_wave, iterations)`. Call `apply_fluctuations` directly.

### 4. Update tests

`test_geological_modulation.py` imports `_TerracedBrownianProfile` directly — update to test `_build_terraced_fluctuations`.

### 5. Verify

Run full test suite, check for any missed imports.

## Before vs After (example: terraced_drift)

**Before:**
```python
from transforms.geological._modulation import apply_profile

@dataclass(frozen=True)
class _TerracedBrownianProfile:
    seed: int = 42
    ...
    def generate(self, length: int) -> list[float]: ...

def apply_terraced_drift_transform(...):
    return apply_profile(tones, _TerracedBrownianProfile(...), dimension, step_size)
```

**After:**
```python
from transforms._modulation import apply_fluctuations

def _build_terraced_fluctuations(length, step_size, quantize_resolution) -> list[float]: ...

def apply_terraced_drift_transform(...):
    fluctuations = _build_terraced_fluctuations(len(tones), step_size, step_size)
    return apply_fluctuations(tones, fluctuations, dimension, step_size)
```
