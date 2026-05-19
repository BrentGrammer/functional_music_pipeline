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
