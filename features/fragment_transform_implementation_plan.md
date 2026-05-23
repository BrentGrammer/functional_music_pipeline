# Iterative Implementation Plan: fragment Transform

## Summary

Implement fragment as a phrase-level geological transform in small reviewable slices. Each slice should be committed/reviewed independently: first parameter
support, then selection logic, then damage behavior, then registry/parser integration and final coverage.

## Iteration 1: Param Support + Skeleton

- Add nullable integer parameter support in transforms/base.py so seed can be omitted or explicitly passed as None.
- Add tests in tests/test_transforms_base.py for nullable integer parsing:
  - accepts None
  - accepts int
  - rejects float, bool, and string values
- Add transforms/geological/fragment.py with:
  - FragmentParams(damage_pct: int, tones_per_fragment: int, seed: int | None)
  - FRAGMENT_PARAMS_SPEC
  - validation for 0 <= damage_pct <= 100
  - validation for tones_per_fragment >= 1
  - placeholder transform functions returning copied input behavior only
- Review checkpoint: param shape and file placement only.

## Iteration 2: Fragment Selection Logic

- Implement pure selection logic in fragment.py.
- Behavior:
  - Empty phrase selects no tones.
  - damage_pct=0 selects no tones.
  - Target damaged count is floor((tone_count \* damage_pct / 100) + 0.5).
  - Any nonzero damage_pct on a nonempty phrase selects at least one tone.
  - damage_pct=100 selects every tone.
  - Full fragments select exactly tones_per_fragment adjacent tones.
  - If fewer than tones_per_fragment tones remain to satisfy damage_pct, create one final partial fragment of exactly the remaining count.
  - Fragment start indexes are random and seed-controlled.
  - Avoid selecting already damaged tones twice; continue choosing valid starts until the target count is reached.
- Add focused tests for:
  - target count calculation
  - exact fragment width
  - final partial fragment behavior
  - same seed produces same selected indexes
  - different seeds can produce different selected indexes
- Review checkpoint: selection behavior only, no musical damage yet.

## Iteration 3: Damage Operations

- Implement damage application for selected tone indexes.
- Behavior:
  - Roll full drop first.
  - Full drop outputs one silent Tone with original duration.
  - If not dropped, independently roll duration shortening and amplitude softening.
  - Shortened duration outputs two tones: shortened original tone plus trailing silence.
  - Shortened tone + trailing silence must equal the original duration.
  - Amplitude softening only lowers amplitude.
- Use internal constants:
  - FULL_DROP_CHANCE = 0.50
  - DURATION_CHIP_CHANCE = 0.45
  - AMPLITUDE_CHIP_CHANCE = 0.45
  - MIN_DURATION_KEEP_RATIO = 0.25
  - MAX_DURATION_KEEP_RATIO = 0.80
  - MIN_AMPLITUDE_KEEP_RATIO = 0.10
  - MAX_AMPLITUDE_KEEP_RATIO = 0.60
- Add tests for:
  - dropped tones become silence with preserved duration
  - shortened tones preserve total timeline duration
  - softened tones never increase amplitude
  - full drop wins over other damage
  - unselected tones remain unchanged
- Review checkpoint: audible transformation behavior.

## Iteration 4: Phrase Transform Integration

- Complete fragment_phrase_transform.
- Flatten the source phrase tones, apply fragment behavior, and return a single transformed motif named "<transformed>", matching existing transform conventions.
- Register fragment in PHRASE_TRANSFORMS only.
- Do not add a score-level transform in v1.
- Add tests for:
  - PHRASE_TRANSFORMS["fragment"] exists
  - parsed params invoke the phrase transform successfully
  - missing seed defaults to None
  - explicit seed=None is accepted
  - score transform registry does not expose fragment
- Review checkpoint: project integration and public API.

## Iteration 5: Acceptance + Regression Pass

- Add end-to-end phrase-level tests using a small phrase with known tones.
- Verify:
  - same seed produces identical transformed tone snapshots
  - different seeds can alter fragment placement or damage result
  - total phrase duration is preserved after transformation
  - damage_pct=0 returns an equivalent phrase
  - invalid params raise ValueError
- Run targeted tests:
  - .venv/bin/pytest tests/test_transforms_base.py -q
  - .venv/bin/pytest tests/test_geological_fragment.py -q
  - .venv/bin/pytest tests/test_transform_wrappers_behavior_happy_path.py -q
- Run broader suite after targeted tests pass:
  - .venv/bin/pytest -q
- Review checkpoint: final behavior and regression results.

## Assumptions

- The implementation lives under transforms/geological/fragment.py.
- The public transform name is fragment.
- Public params are exactly damage_pct, tones_per_fragment, and seed.
- damage_pct controls total damaged original tones; tones_per_fragment controls normal chunk width.
- Fragment start positions must be stochastic; seed only makes them reproducible.
- Timeline preservation is required for both full drops and shortened tones.
