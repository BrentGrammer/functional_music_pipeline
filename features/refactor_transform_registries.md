# Feature: Split Transform Registries (Phrase vs. Score)

## Problem
Currently, the application uses a single, flat `TRANSFORMS` registry. This forces a redundant naming convention where score-level transforms must be prefixed with `score_` (e.g., `score_reverse`, `score_transpose`) to avoid key collisions with phrase-level transforms.

This is a "leaky abstraction" that forces the user to know internal implementation details in the JSON composition file.

## Goal
To separate transforms into two distinct registries: `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`. This will allow the same name (e.g., `reverse`) to be used in both the `phrase` and `score_transforms` blocks of a JSON composition, with the parser automatically selecting the correct implementation based on context.

## Proposed Changes

### 1. `transforms/registry.py`
- Replace the single `TRANSFORMS` dictionary with two dictionaries:
  - `PHRASE_TRANSFORMS`: Contains all transforms that operate on a single sequence of tones.
  - `SCORE_TRANSFORMS`: Contains transforms that operate on a `Score` object (including `EachVoiceTransform` wrappers, `ScoreTransform`, and `ScoreTargetMotifsTransform`).
- Remove the `score_` prefix from names in the `SCORE_TRANSFORMS` registry.

### 2. `composition/parser.py`
- Update `_apply_phrase_transform_specs` to look up names in `PHRASE_TRANSFORMS`.
- Update `_apply_score_transform_spec` to look up names in `SCORE_TRANSFORMS`.
- Ensure helpful error messages if a transform is used in the wrong scope.

### 3. Composition Demos
- Update all JSON files in `compositions/` to remove the `score_` prefix from transforms inside `score_transforms` blocks.

## Implementation Plan

1.  **Preparation:**
    *   Verify all existing transforms and their intended scopes.
2.  **Refactor `transforms/registry.py`:**
    *   Split the dictionary.
    *   Rename score-level keys.
3.  **Update `composition/parser.py`:**
    *   Modify lookup logic for phrase and score levels.
4.  **Update Compositions:**
    *   Surgically update all `.json` files in `compositions/`.
5.  **Verification:**
    *   Run existing tests.
    *   Render all updated compositions to ensure no regressions.
    *   Add a new test case verifying that "reverse" works correctly in both scopes.

## Benefits
- **Improved UX:** Cleaner JSON schema for users.
- **Cleaner Domain Model:** Explicit separation between local (phrase) and global (score) effects.
- **Better API Foundation:** Simplifies dropdown population and validation for future UIs.
