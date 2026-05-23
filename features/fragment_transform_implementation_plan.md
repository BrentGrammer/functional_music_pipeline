# TDD Implementation Plan: fragment Transform

## Summary

Implement `fragment` as a phrase-level geological transform in small reviewable slices. Start by writing acceptance tests for the observable behavior the feature must satisfy, then implement toward those tests.

## Workflow

- Write the core acceptance tests before production implementation.
- Use a red-green loop where it is useful, but do not treat it dogmatically.
- It is acceptable for tests to remain red during a breaking feature slice as long as they are green by the end of the full implementation.
- Prefer observable phrase output over private implementation assertions.
- Test through the public transform registry or phrase transform function whenever practical.
- Avoid asserting private selected indexes, RNG call order, or helper function internals.
- Do not add throwaway temporary behavior just to make intermediate tests pass.
- If an iteration needs multiple production pieces before observable behavior can pass, keep those tests red until the real behavior is implemented.
- Keep each iteration independently reviewable.
- Stop after each iteration for review before moving on.

## Iteration 1: Public Acceptance Tests + Skeleton

- Write failing acceptance tests first for the public feature shape:
  - `fragment` is registered in `PHRASE_TRANSFORMS`.
  - `fragment` is not registered in `SCORE_TRANSFORMS`.
  - `damage_pct=0` returns an equivalent phrase.
  - omitted `damage_pattern_key` is accepted and treated as no fixed reusable pattern.
  - provided `damage_pattern_key` is accepted when it is a string.
  - invalid `damage_pattern_key` values are rejected through normal string param validation.
- Add transforms/geological/fragment.py with:
  - FragmentParams(damage_pct: int, damage_tones_chunk_size: int, damage_pattern_key: str | None)
  - FRAGMENT_PARAMS_SPEC
  - validation for 0 <= damage_pct <= 100
  - validation for damage_tones_chunk_size >= 1
  - no-op behavior for `damage_pct=0`
- When `damage_pattern_key` is present, derive the random source from a stable hash such as SHA-256, not Python's built-in hash.
- Review checkpoint: public API exists and no-op behavior works.

## Iteration 2: Fragment Selection + Real Damage

- Keep top-level acceptance tests simple. Do not make acceptance tests reverse-engineer chunk placement from fully transformed phrase output because shortened tones can emit trailing silence and make that hard to read.
- Write focused selection-level tests for exact chunk placement behavior before implementing selection. These tests may target a small, explicit selection function because chunk placement is business behavior worth testing directly.
- Implement fragment selection and real damage behavior together before expecting this test group to pass.
- Behavior:
  - Empty phrase selects no tones.
  - damage_pct=0 selects no tones.
  - Target damaged count is floor((tone_count \* damage_pct / 100) + 0.5).
  - Any nonzero damage_pct on a nonempty phrase selects at least one tone.
  - damage_pct=100 selects every tone.
  - Full fragments select exactly damage_tones_chunk_size adjacent tones.
  - If fewer than damage_tones_chunk_size tones remain to satisfy damage_pct, create one final partial fragment of exactly the remaining count.
  - Fragment start indexes are random and controlled by `damage_pattern_key` when one is provided.
  - Avoid selecting already damaged tones twice.
  - Choose from currently valid fragment starts rather than retrying indefinitely.
  - When no full-width start remains but damage count remains, create the final partial fragment from a valid remaining adjacent run.
  - Every selected original-tone position must receive at least one actual damage operation.
- Damage behavior:
  - Roll full drop first.
  - Full drop outputs one silent Tone with original duration.
  - If not dropped, independently roll duration shortening and amplitude softening.
  - If both non-drop rolls fail, force one non-drop chip so the selected tone is observably damaged.
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
- Add focused observable tests for:
  - `damage_pct` controls how many original-tone positions are changed in the resulting phrase.
  - same `damage_pattern_key` produces the same changed-position pattern and transformed tone snapshot.
  - different `damage_pattern_key` values can produce a different changed-position pattern or transformed tone snapshot.
  - dropped tones become silence with preserved duration
  - shortened tones preserve total timeline duration
  - softened tones never increase amplitude
  - full drop wins over other damage
  - unselected tones remain unchanged
- Add focused selection-level tests for:
  - `damage_tones_chunk_size` repeats as the normal adjacent chunk width until the target damage count is reached.
  - If the remaining target damage count is smaller than `damage_tones_chunk_size`, only the final chunk may be smaller.
  - Multiple full chunks can appear in different parts of the phrase when the target damage count is large enough.
  - Selected tone positions are not selected twice.
  - The selected tone count equals the target count derived from `damage_pct`.
- Review checkpoint: stochastic fragment placement and audible transformation behavior are observable through phrase output.

## Iteration 3: Phrase Transform Integration

- Write failing tests first for phrase-level registry and parser integration through the normal transform path.
- Complete fragment_phrase_transform.
- Flatten the source phrase tones, apply fragment behavior, and return a single transformed motif named "<transformed>", matching existing transform conventions.
- Register fragment in PHRASE_TRANSFORMS only.
- Do not add a score-level transform in v1.
- Add tests for:
  - parsed params invoke the phrase transform successfully
  - registry-based usage produces the same observable behavior as direct phrase-transform usage
  - invalid params fail through the registry path
- Review checkpoint: project integration and public API.

## Iteration 4: Acceptance + Regression Pass

- Add final end-to-end acceptance tests using a small phrase with known tones.
- Verify:
  - same `damage_pattern_key` produces identical transformed tone snapshots
  - different `damage_pattern_key` values can alter fragment placement or damage result
  - total phrase duration is preserved after transformation
  - damage_pct=0 returns an equivalent phrase
  - nonzero damage creates at least one silent, shortened, or softened remnant
  - invalid params raise ValueError
- Run targeted tests:
  - .venv/bin/pytest tests/test_geological_fragment.py -q
  - .venv/bin/pytest tests/test_transform_wrappers_behavior_happy_path.py -q
- Run broader suite after targeted tests pass:
  - .venv/bin/pytest -q
- Review checkpoint: final behavior and regression results.

## Assumptions

- The implementation lives under transforms/geological/fragment.py.
- The public transform name is fragment.
- Public params are exactly damage_pct, damage_tones_chunk_size, and damage_pattern_key.
- damage_pct controls total damaged original tones; damage_tones_chunk_size controls normal chunk width.
- Fragment start positions must be stochastic; damage_pattern_key only makes a specific stochastic result reproducible.
- Timeline preservation is required for both full drops and shortened tones.

## Handoff

Current state at handoff:

- Iteration 1 skeleton exists in `transforms/geological/fragment.py`.
- `fragment` is registered as a phrase transform only.
- `FRAGMENT_PARAMS_SPEC` exists for `damage_pct`, `damage_tones_chunk_size`, and `damage_pattern_key`.
- `damage_pct=0` currently returns an equivalent transformed phrase.
- Nonzero `damage_pct` still raises `NotImplementedError`.

Current test state:

- `tests/test_geological_fragment.py` contains the iteration 1 public API coverage and top-level acceptance tests.
- The simple top-level acceptance tests are the right shape:
  - same `damage_pattern_key` repeats the same result
  - different `damage_pattern_key` values can change the result
  - total phrase duration is preserved while the phrase changes
- Additional chunk-size acceptance tests were explored and became too complex at the top-level output boundary.
- The user explicitly wants exact chunk-shape behavior tested, but not through acceptance tests that reverse-engineer transformed output.

Important testing boundary decisions:

- Top-level acceptance tests should remain at the business-layer entry point using `generate_score_plan(...)` and `transform_score(...)`.
- Those acceptance tests should stay simple, self-contained, and readable without helper-heavy reconstruction logic.
- Exact chunk placement rules belong in focused selection-level tests, likely around a small explicit selection function introduced for that purpose.

User preferences that should be preserved next session:

- Keep tests self-contained. Do not force the reader to scroll to module-level constants just to understand a test case.
- Avoid overly clever acceptance-test logic with bookkeeping loops, output reconstruction, or dense helper behavior inline.
- Prefer regular local variable names over all-caps extracted constants inside tests.
- The broader design concern about param-validation sprawl was recorded in `features/current/centralize_transform_param_validation.md`.

Targeted test status before clearing context:

- `tests/test_geological_fragment.py` was red because nonzero `fragment` behavior is not implemented yet.
- The expected red boundary should remain tied to missing implementation, not to confusing or unstable test design.

Next smallest step:

1. Clean up `tests/test_geological_fragment.py` so only the simple top-level acceptance tests remain at that level.
2. Add focused selection-level tests for exact chunk behavior:
   - repeated full chunks
   - final partial chunk only when needed
   - no duplicate selected positions
   - selected count matches the `damage_pct` target
3. Only after those tests exist, implement the explicit fragment-selection function and then the real damage behavior.
