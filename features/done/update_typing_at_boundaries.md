Best practice for a clean codebase is:

1. Public boundary functions accept object (or broad input) when they parse external/untrusted data.
2. Validate immediately at that boundary.
3. Then convert/narrow to strong internal types (TypedDict/dataclasses) for the rest of the pipeline.
4. Keep strict typed signatures for internal functions that assume valid data.

Why:

- External JSON is untyped at runtime.
- If boundary functions are strictly typed, tests for invalid input become awkward/noisy.
- You still get strong typing internally, where it provides the most value.

For your case:

- generate_score_plan(...) should be boundary-style (accept broad input + validate).
- Internal helpers after validation can use CompositionDocument, VoiceConfig, PhraseConfig, etc.
- This keeps runtime validation honest and mypy clean without massive test churn.

## Parser-specific decision

We reviewed the current parser flow in `composition/parser.py` and found that the top-level structure is being validated more than once.

Current shape:

- `generate_score_plan(...)` accepts broad input and calls `_validate_composition_structure(...)`.
- `_extract_composition_sections(...)` then calls `_validate_composition_structure(...)` again.
- `_extract_composition_sections(...)` also re-checks `motifs`, `composition`, `voices`, and `score_transforms` after saying it assumes validation already happened.
- Other internal helpers such as `_extract_phrase_transform_requests(...)` and `_create_voice_plans_from_document(...)` still accept broad `object` inputs and repeat shape checks internally.

This is a design smell, not just a test smell.

Why:

- Once the document has crossed the parser boundary and passed structural validation, internal parser helpers should not keep acting as though they are still handling arbitrary hostile input.
- The current duplicate checks force tests to cover unrealistic cases where a custom mapping returns valid data on one read and invalid data on the next.
- The `FlakyDocument` / `FlakyComposition` tests in `tests/test_parser.py` are only necessary because the parser currently does not trust its own validated intermediate state.

## Decision

We want the broader refactor, not the minimal patch.

The parser should move to a one-pass trust model:

1. `generate_score_plan(...)` remains the public boundary and accepts broad external input.
2. Top-level composition structure is validated once at that boundary.
3. After validation, the parser should narrow into trusted internal section types and pass those through the rest of the parser pipeline.
4. Internal helpers should use narrower signatures that reflect already-validated data instead of re-validating top-level structure.
5. Tests should stop modeling time-varying hostile mappings just to justify repeated internal validation.

## Practical implications for the refactor

- `_extract_composition_sections(...)` should stop re-validating the document and should become an extraction/narrowing step over already-validated input.
- `voices_section` and `score_transforms_section` should become trusted internal values after the boundary validation step, not repeatedly treated as `object`.
- Helper signatures should be updated toward `CompositionDocument`, `CompositionConfig`, `VoiceConfig`, `PhraseConfig`, and `TransformConfig` where appropriate.
- Lower-level validation should remain where it is still semantically needed because the helper is validating its own direct input shape, but repeated validation of the same top-level composition sections should be removed.
- Parser tests should be updated to reflect the new contract:
  - boundary tests cover invalid external input
  - internal helper tests cover their real responsibilities
  - flaky re-read tests that depend on mutating `dict.get(...)` behavior should be removed or replaced

## Goal of this change

The goal is not just to make tests simpler. The goal is to make the parser architecture honest:

- broad types and runtime validation at the boundary
- narrow trusted types internally
- fewer duplicate checks
- fewer defensive branches against unrealistic pipeline mutation
- cleaner contracts that match how the application is actually supposed to work

## Final validation plan

- composition
  - required
  - empty object forbidden
- voices
  - may be missing, normalized to []
  - empty list allowed
- phrase motifs
  - required
  - empty list forbidden
- phrase transforms
  - may be missing, normalized to []
  - empty list allowed
- score_transforms
  - may be missing, normalized to []
  - empty list allowed

## Plan remaining: Separate input schema types from internal schema

- the domain shape is not actually different in kind
  - only the guarantees are different
  - naming a second parallel tree ValidatedX can create duplication and cognitive noise

  A cleaner approach here is usually one of these:
  1. Keep one schema type layer and make the validator construct values that genuinely satisfy it.
     - This works best if the schema types describe the post-boundary contract.
     - Missing optional fields that you normalize should stop being optional if internal code always expects them.
  2. Split Input vs internal/domain names, not Validated.
     - Example:
       - TransformConfigInput
       - TransformConfig
     - That is more conventional because it distinguishes external wire format from internal trusted structure.

  For this codebase, I think option 2 is the better fit if you want a split at all.

  So instead of ValidatedPhraseConfig, I’d recommend:
  - PhraseConfigInput for raw JSON-ish input
  - PhraseConfig for normalized internal parser use

  Same for:
  - TransformConfigInput / TransformConfig
  - CompositionDocumentInput / CompositionDocument

  That keeps the names honest:
  - one is external input
  - one is internal trusted shape

  So the next step should be reframed as:
  - rename the current schema types to \*Input
  - introduce the internal trusted \*Config / CompositionDocument names
  - have \_validate_composition_structure() return the internal trusted document type

## Handoff for where to pick back up:

Current State

- Tests are green.
- The parser boundary has been mostly split into \*Input vs internal types.
- Runtime validation/normalization is happening at the boundary.
- mypy is still noisy and should be cleaned up after the migration is fully propagated.

Remaining Steps

1. Remove any remaining redundant internal typed-dict rebuilding.
   - Audit composition/parser.py for places still reconstructing PhraseConfig, VoiceConfig, or TransformConfig after boundary normalization.
   - Keep only one normalization point.
2. Review whether parse_motifs() should stay as-is or be folded into the boundary step.
   - Decide if motif parsing belongs as a separate “raw strings -> domain tones” step or if it should be merged into a more explicit parsing seam.
   - Likely keep it separate unless there is obvious duplication.
3. Decide whether CompositionDocument and CompositionConfig should remain the internal parser types, or whether some remaining tests/helpers still need more
   \*Input propagation.
   - This is mostly a consistency audit now.
4. Propagate \*Input annotations through any remaining raw document builders in tests.
   - Especially helper functions in tests that assemble raw composition dicts.
   - Goal: raw JSON-ish data always uses \*Input; internal parser data always uses non-Input.
5. Audit the parser for any remaining fallback-style access that contradicts the trusted internal contract.
   - For example any lingering .get(..., default) on internal types where the field is now guaranteed.
   - Remove only if the boundary contract already guarantees the field.
6. Run and fix mypy.
   - After the schema migration is fully settled, clean up the type fallout.
   - This should include:
     - stale type: ignore
     - mismatched test annotations
     - any remaining return-type or TypedDict incompatibilities
     - unrelated mypy issues only if they block a clean run
7. Final cleanup pass on naming and dead code.
   - Remove any now-unused imports, old aliases, or helper comments.
   - Check for any confusing names left over from the migration.

Likely First Next Step

- Start with a parser audit for redundant rebuilding/conversion and leftover .get() usage in trusted internal code.
- That should be the smallest safe next move before tackling mypy.

Handoff Summary

- Direction remains: validate and normalize once at the boundary, trust internally.
- Raw types use \*Input.
- Internal parser types use non-Input.
- Domain objects (Motif, Tone, etc.) remain the next layer after parser normalization.
- Do not introduce new behavior while finishing the migration; prioritize consistency and type cleanup.
