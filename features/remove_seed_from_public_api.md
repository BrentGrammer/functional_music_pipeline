# Remove Seed from Public API

## Goal

Remove the `seed` parameter from the public API of all transforms that currently expose it. Users should not need to understand or manage seed values to use stochastic transforms. Instead, transforms should handle randomness internally while providing a user-friendly `new_pattern_each_use` boolean for controlling whether repeated uses produce distinct patterns.

## Background

The `ridged_drop` transform was successfully updated to hide `seed` and expose `new_pattern_each_use` instead. This pattern should be applied to the remaining transforms that still expose `seed`.

## Affected Transforms

| Transform | File | Current Seed Usage |
|-----------|------|-------------------|
| `cellular_automata` / `score_cellular_automata` | `transforms/complexity/cellular_automata.py` | Optional, default 42 |
| `random_drop` / `score_random_drop` | `transforms/complexity/random_drop.py` | Optional, default 42 |
| `weierstrass` / `score_weierstrass` | `transforms/complexity/weierstrass.py` | Optional, default 42 |
| `terraced_drift` / `score_terraced_drift` | `transforms/geological/terraced_drift.py` | Optional, default 42 |
| `accelerando` / `ritardando` | `transforms/tempo/_common.py` | Optional, used when `jaggedness` is non-zero |

## Proposed API Change

For each affected transform, replace:

```python
seed: int = 42
```

With:

```python
new_pattern_each_use: bool = False
```

Behavior:
- `new_pattern_each_use=False` (default): Use a fixed internal seed (42) for deterministic, reproducible results.
- `new_pattern_each_use=True`: Generate a random seed internally on each call, producing distinct patterns.

## Implementation Checkpoints

### 1. Update `weierstrass` Transform

Scope:
1. Remove `seed` from `WEIERSTRASS_PARAMS_SPEC`.
2. Add `new_pattern_each_use` with `BooleanParam` schema.
3. Update `apply_weierstrass_transform` to generate random seed when `new_pattern_each_use=True`.
4. Update tests to use new API.
5. Update any demos that use `seed`.

Verification:

```shell
pytest tests/test_complexity_modulation.py
```

Stop for review.

### 2. Update `cellular_automata` Transform

Scope:
1. Remove `seed` from `CELLULAR_AUTOMATA_PARAMS_SPEC`.
2. Add `new_pattern_each_use` with `BooleanParam` schema.
3. Update `apply_cellular_automata_transform` to generate random seed when `new_pattern_each_use=True`.
4. Update tests to use new API.
5. Update any demos that use `seed`.

Verification:

```shell
pytest tests/test_complexity_modulation.py
```

Stop for review.

### 3. Update `random_drop` Transform

Scope:
1. Remove `seed` from `RANDOM_DROP_PARAMS_SPEC`.
2. Add `new_pattern_each_use` with `BooleanParam` schema.
3. Update `apply_random_drop_transform` to generate random seed when `new_pattern_each_use=True`.
4. Update tests to use new API.
5. Update any demos that use `seed`.

Verification:

```shell
pytest tests/test_complexity_modulation.py
```

Stop for review.

### 4. Update `terraced_drift` Transform

Scope:
1. Remove `seed` from `TERRACED_DRIFT_PARAMS_SPEC`.
2. Add `new_pattern_each_use` with `BooleanParam` schema.
3. Update `apply_terraced_drift_transform` to generate random seed when `new_pattern_each_use=True`.
4. Update tests to use new API.
5. Update any demos that use `seed`.

Verification:

```shell
pytest tests/test_geological_modulation.py
```

Stop for review.

### 5. Update `accelerando` and `ritardando` Transforms

Scope:
1. Remove `seed` from tempo params spec.
2. Add `new_pattern_each_use` with `BooleanParam` schema.
3. Update tempo transforms to generate random seed when `new_pattern_each_use=True` and `jaggedness` is non-zero.
4. Update tests to use new API.
5. Update any demos that use `seed`.

Verification:

```shell
pytest tests/test_tempo_transforms.py
```

Stop for review.

### 6. Update README Documentation

Scope:
1. Remove all references to `seed` parameter in transform documentation.
2. Add `new_pattern_each_use` to each affected transform's documentation.
3. Update example JSON snippets.

Stop for review.

### 7. Update Demo Files

Scope:
1. Review all demo files in `compositions/` folder.
2. Remove `seed` from any transform that no longer supports it.
3. Add `new_pattern_each_use: true` examples where appropriate to demonstrate the feature.

Verification:

```shell
for file in compositions/*.json; do python -c "import json; json.load(open('$file'))"; done
```

Stop for review.

### 8. Final Test Pass

Scope:
1. Run full test suite.
2. Run mypy type checking.
3. Fix any issues.

Verification:

```shell
pytest tests/
mypy .
```

Stop for final review.

## Design Decisions

### Why Remove Seed?

1. **User-unfriendly**: Arbitrary integer values like `42` or `100` have no musical meaning.
2. **Implementation detail**: Seeds are an internal mechanism for reproducibility, not a creative control.
3. **Confusing**: Users may not understand why changing the seed changes the output.

### Why Add `new_pattern_each_use`?

1. **Clear intent**: The name describes what the user gets - a new pattern or the same pattern.
2. **Boolean simplicity**: Two clear choices instead of infinite arbitrary integers.
3. **Preserves reproducibility**: Default `false` keeps deterministic behavior for testing and sharing compositions.

### Internal Seed Strategy

When `new_pattern_each_use=True`, use:

```python
_DEFAULT_SEED = 42
_RANDOM_SEED_UPPER_BOUND = 2 ** 31
seed = random.randint(0, _RANDOM_SEED_UPPER_BOUND) if new_pattern_each_use else _DEFAULT_SEED
```

This matches the pattern established in `ridged_drop`.

## Open Questions

1. Should we add a global composition-level seed for full reproducibility of stochastic compositions?
2. Should transforms that don't currently use randomness (but could) also get `new_pattern_each_use` for future-proofing?

## References

- `features/simplify_ridged_drop_transform.md` - Completed implementation of this pattern for `ridged_drop`.
- `transforms/geological/ridged_drop.py` - Reference implementation.
