# Fix Golden Ratio Phrase Relative behavior

- The behavior of the phrase relative golden ratio grow/shrink transforms is not correct.
- Each successive phrase should be transformed from the last in a pipeable fashion, but if 2 consecutive phrases are grown/shrunk the third resulting phrase is not changed in proportion to the second transformed phrase that came before it.

## Implementation Plan

1. Add a failing regression test for compositions/golden_ratio_phrase_relative_shrink.json. Expected phrase duration totals should be roughly 8.0, 8.0 / GOLDEN_RATIO, then
   8.0 / GOLDEN_RATIO / GOLDEN_RATIO.
2. Add a focused unit test for the phrase-relative lookup behavior: when transforming phrase index 2, the transform should compare only against phrase index 1, using the
   already-transformed score state.
3. Centralize “previous phrase tones” into one shared helper, likely in score_model/traversal.py or transforms/base.py. It should return:
   - immediately previous phrase in the same voice when phrase_index > 0
   - existing cross-voice fallback only when this is the first phrase in a later voice
4. Update transforms/proportion/golden_ratio.py to use that helper. Keep phrase_relative_golden_ratio_shrink() itself unchanged because its signature is already clean: it
   receives tones and previous_tones.
5. Update transforms/proportion/feigenbaum.py the same way, since it appears to have the same bug.
6. Run targeted tests:
   - .venv/bin/pytest tests/test_proportion_golden_ratio.py -q
   - .venv/bin/pytest tests/test_proportion_feigenbaum.py -q
   - whichever composition/parser test gets the new demo regression
7. Run the broader suite after targeted tests pass:
   - .venv/bin/pytest -q

Review checkpoints:

- After step 1, you can review the failing test and expected behavior before code changes.
- After steps 3-5, you can review the actual fix before I run the full suite.
- After tests pass, we can optionally regenerate/listen to the WAV as a final manual verification.
