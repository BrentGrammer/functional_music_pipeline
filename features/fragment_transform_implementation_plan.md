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
  - omitted `repeatable_damage_key` is accepted and treated as no fixed reusable pattern.
  - provided `repeatable_damage_key` is accepted when it is a string.
  - invalid `repeatable_damage_key` values are rejected through normal string param validation.
- Add transforms/geological/fragment.py with:
  - FragmentParams(damage_pct: int, damage_tones_chunk_size: int, dimension: ToneDimension | None, repeatable_damage_key: str | None)
  - FRAGMENT_PARAMS_SPEC
  - validation for 0 <= damage_pct <= 100
  - validation for damage_tones_chunk_size >= 1
  - no-op behavior for `damage_pct=0`
- Add an optional `dimension` param using the existing `ToneDimensionParam`.
  - Default is `None`.
  - `None` means multi-dimensional stochastic fragmentation.
  - A provided `ToneDimension` restricts damage to that dimension.
- When `repeatable_damage_key` is present, derive the random source from a stable hash such as SHA-256, not Python's built-in hash.
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
  - Fragment start indexes are random and controlled by `repeatable_damage_key` when one is provided.
  - Avoid selecting already damaged tones twice.
  - Choose from currently valid fragment starts rather than retrying indefinitely.
  - When no full-width start remains but damage count remains, create the final partial fragment from a valid remaining adjacent run.
  - Every selected original-tone position must receive at least one actual damage operation.
- Damage behavior when `dimension` is omitted:
  - Roll tone removal first.
  - Tone removal outputs one silent Tone with original duration.
  - If not removed, independently roll duration damage and amplitude damage.
  - If both non-removal rolls fail, force one non-removal damage so the selected tone is observably changed.
  - Shortened duration outputs two tones: shortened original tone plus trailing silence.
  - Shortened tone + trailing silence must equal the original duration.
  - Amplitude damage only lowers amplitude.
- Damage behavior when `dimension` is provided:
  - ToneDimension.FREQUENCY: every selected tone is replaced with silence for its original duration.
  - ToneDimension.DURATION: every selected tone is shortened and followed by trailing silence. No tone-removal roll or amplitude damage is applied.
  - ToneDimension.AMPLITUDE: every selected tone has amplitude reduced. No tone-removal roll or duration damage is applied.
  - Selected tones must always be observably changed within the selected dimension.
- Use internal constants:
  - TONE_REMOVAL_CHANCE = 0.50
  - DURATION_DAMAGE_CHANCE = 0.45
  - AMPLITUDE_DAMAGE_CHANCE = 0.45
  - MIN_DURATION_AFTER_DAMAGE_SECONDS = 0.03
  - MAX_DURATION_AFTER_DAMAGE_RATIO = 0.99
  - MIN_AMPLITUDE_REDUCTION_DECIBELS = 0.1
  - MAX_AMPLITUDE_REDUCTION_DECIBELS = 20.0
- Add focused observable tests for:
  - `damage_pct` controls how many original-tone positions are changed in the resulting phrase.
  - same `repeatable_damage_key` produces the same changed-position pattern and transformed tone snapshot.
  - different `repeatable_damage_key` values can produce a different changed-position pattern or transformed tone snapshot.
  - removed tones become silence with preserved duration
  - shortened tones preserve total timeline duration
  - softened tones never increase amplitude
  - tone removal wins over other damage in multi-dimensional mode
  - unselected tones remain unchanged
  - omitted `dimension` keeps the multi-dimensional stochastic behavior
  - `dimension=frequency` only creates silence for selected tones
  - `dimension=duration` only shortens selected tones and preserves the phrase timeline
  - `dimension=amplitude` only reduces selected tone amplitudes
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
  - parsed `dimension` strings invoke the dimension-bound phrase transform successfully
  - registry-based usage produces the same observable behavior as direct phrase-transform usage
  - invalid params fail through the registry path
- Review checkpoint: project integration and public API.

## Iteration 4: Acceptance + Regression Pass

- Add final end-to-end acceptance tests using a small phrase with known tones.
- Verify:
  - same `repeatable_damage_key` produces identical transformed tone snapshots
  - different `repeatable_damage_key` values can alter fragment placement or damage result
  - total phrase duration is preserved after transformation
  - damage_pct=0 returns an equivalent phrase
  - nonzero damage creates at least one silent, shortened, or softened remnant
  - omitted `dimension` uses multi-dimensional stochastic behavior
  - explicit `dimension` restricts damage to only that dimension
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
- Public params are damage_pct, damage_tones_chunk_size, optional dimension, and repeatable_damage_key.
- damage_pct controls total damaged original tones; damage_tones_chunk_size controls normal chunk width.
- Fragment start positions must be stochastic; repeatable_damage_key only makes a specific stochastic result reproducible.
- Timeline preservation is required for both tone removal and shortened tones.
- Reuse the existing `ToneDimension` and parser support for `dimension`.
- Omitted `dimension` means multi-dimensional stochastic fragmentation, not a new enum value.

## Handoff

Current state at handoff:

- `fragment` is implemented in `transforms/geological/fragment.py` as a phrase transform only.
- `FragmentParams` and `FRAGMENT_PARAMS_SPEC` now include:
  - `damage_pct`
  - `damage_tones_chunk_size`
  - optional `dimension`
  - optional `repeatable_damage_key`
- Omitted `dimension` now means multi-dimensional stochastic fragmentation.
- Explicit `dimension` values now work:
  - `ToneDimension.FREQUENCY`
  - `ToneDimension.DURATION`
  - `ToneDimension.AMPLITUDE`
- `damage_pct=0` returns an equivalent transformed phrase.
- Nonzero `damage_pct` no longer raises `NotImplementedError`.
- Chunk selection is implemented in `_select_chunks_to_damage(...)`.
- Multi-dimensional selected-tone damage is implemented in `_damage_selected_tone_across_dimensions(...)`.
- Explicit dimension-bound damage is implemented in `_damage_selected_tone_for_dimension(...)`.

Current test state:

- `tests/test_geological_fragment.py` is green and now covers:
  - public API / params parsing
  - no-op behavior for `damage_pct=0`
  - focused chunk-selection behavior
  - repeatability via `repeatable_damage_key`
  - top-level multi-dimensional acceptance behavior
  - explicit `dimension` behavior for frequency, duration, and amplitude
- `tests/test_transform_wrappers_behavior_happy_path.py` is green after the fragment changes.

Important testing boundary decisions:

- Top-level acceptance tests should remain at the business-layer entry point using `generate_score_plan(...)` and `transform_score(...)`.
- Those acceptance tests should stay simple, self-contained, and readable without helper-heavy reconstruction logic.
- Exact chunk placement rules belong in focused selection-level tests, not in acceptance tests that reconstruct transformed output in detail.

User preferences that should be preserved next session:

- Keep tests self-contained. Do not force the reader to scroll to module-level constants just to understand a test case.
- Avoid overly clever acceptance-test logic with bookkeeping loops, output reconstruction, or dense helper behavior inline.
- Prefer regular local variable names over all-caps extracted constants inside tests.
- Keep the code boring, predictable, and explicit. The user is sensitive to helpers or indirection that blur mode boundaries.
- Avoid wrapper helpers that only rename or forward behavior without removing real complexity.
- The broader design concern about param-validation sprawl was recorded in `features/current/centralize_transform_param_validation.md`.

Targeted verification completed:

- `.venv/bin/pytest tests/test_geological_fragment.py -q`
  - Result: passing (`25 passed` at last run).
- `.venv/bin/pytest tests/test_transform_wrappers_behavior_happy_path.py -q`
  - Result: passing (`11 passed` at last run).
- `.venv/bin/python -m mypy tests/test_geological_fragment.py`
  - Result: passing.

Next smallest step:

1. Do a focused readability pass on `transforms/geological/fragment.py`, especially the selected-tone damage helpers and dispatch flow.
2. Keep behavior unchanged while simplifying names or control flow that still reads as muddled.
3. After that cleanup, run:
   - `.venv/bin/pytest tests/test_geological_fragment.py -q`
   - `.venv/bin/pytest tests/test_transform_wrappers_behavior_happy_path.py -q`
4. If the fragment file is still hard to follow after that pass, identify one specific confusing block at a time and simplify it without starting a broad refactor.
