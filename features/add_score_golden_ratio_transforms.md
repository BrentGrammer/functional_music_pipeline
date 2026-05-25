## Add Explicit Score Golden Ratio Grow/Shrink Transforms

Did we do this already? check if it's done.

### Summary

Introduce two explicit score-scope Golden Ratio transforms named score_golden_ratio_shrink and score_golden_ratio_grow. These will operate at score scope only, scaling each
voice independently across the selected dimension. Do not keep golden_ratio as a score-scope alias.

### Key Changes

- In the Golden Ratio proportion module, add a reusable non-relative tone-level grow helper alongside the existing shrink helper:
  - golden_ratio_transform_shrink keeps multiplying the selected dimension by 1 / GOLDEN_RATIO.
  - golden_ratio_transform_grow multiplies the selected dimension by GOLDEN_RATIO.
- Replace the current score-level golden_ratio transform function shape with explicit score-scope transform functions:
  - score_golden_ratio_shrink_transform
  - score_golden_ratio_grow_transform
- Remove golden_ratio from SCORE_TRANSFORMS and register two explicit score transform names:
  - score_golden_ratio_shrink
  - score_golden_ratio_grow
- Keep the existing phrase-scope golden_ratio behavior unchanged.
- Keep the existing phrase-relative transforms unchanged:
  - phrase_relative_golden_ratio_shrink
  - phrase_relative_golden_ratio_grow
- Update imports anywhere tests or modules currently import golden_ratio_score_transform.

### Behavior

- score_golden_ratio_shrink:
  - For each voice, flatten the voice to tones and multiply the selected dimension by 1 / GOLDEN_RATIO.
  - Preserve the current score-transform behavior of rebuilding each voice as a single transformed phrase.
- score_golden_ratio_grow:
  - For each voice, flatten the voice to tones and multiply the selected dimension by GOLDEN_RATIO.
  - Match the same output structure as the shrink version.

### Tests

- Add unit coverage for the new score grow transform.
- Update score-transform registry/parser-facing tests to use the new explicit score transform names.
- Add parser/registry coverage showing that golden_ratio is rejected in score_transforms while still accepted in phrase transforms.
- Add or update a high-level score-transform regression that verifies:
  - score_golden_ratio_shrink reduces each voice total proportionally
  - score_golden_ratio_grow increases each voice total proportionally
- Model these high-level regressions after the recent phrase-relative Golden Ratio composition regressions in tests/test_proportion_golden_ratio.py:
  - build an in-memory composition_document
  - run transform_score(generate_score_plan(composition_document))
  - assert on observable rendered score totals
  - avoid manually stepping individual transform functions in the regression
- Verify phrase-scope golden_ratio still works unchanged.
- Use dimension: duration for proportional total assertions so amplitude clamping cannot make exact total scaling ambiguous.

### Assumptions

- golden_ratio will no longer be available as a score-scope transform name.
- The current score-scope behavior of flattening each voice into one phrase remains unchanged.
- No new params are needed; both transforms continue using the existing optional dimension param.
- README documentation should describe golden_ratio as phrase-scope behavior and list score_golden_ratio_shrink / score_golden_ratio_grow as the score-scope options.
