# Split Synthetic Motif Name Cleanup Note

## Summary

Move the synthetic motif-name work out of features/current/cleanup_registry_inline_lambdas.md into its own feature note, because registry inline-lambda
cleanup is complete independently from motif naming.

## Key Changes

- Create features/current/synthetic_motif_name_cleanup.md.
- Move the current Step 11 content and the “Open Item: Synthetic Motif Names” section into the new file.
- In cleanup_registry_inline_lambdas.md, replace those sections with a short note that synthetic motif names are tracked separately in
  synthetic_motif_name_cleanup.md.
- Keep the new note focused on the motif-name issue, including:
  - current fake names like "<transformed>", "<each_voice>", "<parsed>", "<frost_copy>", "<frost>", "<feigenbaum>", and "<pedal>";
  - why generated motifs do not have meaningful user-authored names;
  - options considered;
  - current recommended direction: make Motif.name optional as the real fix, rather than replacing fake names with "".

## Test Plan

- No runtime tests needed for documentation-only changes.
- Verify with rg -n "Step 11|Open Item: Synthetic Motif Names|synthetic motif" features/current/cleanup_registry_inline_lambdas.md features/current/
  synthetic_motif_name_cleanup.md.

## Assumptions

- This is a documentation split only.
- No production code or tests should change as part of this step.
- The new note should preserve the existing discussion but clarify that motif naming is separate from registry cleanup.
