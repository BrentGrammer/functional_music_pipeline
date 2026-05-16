# Feature: Split Transform Registries (Phrase vs. Score)

## Problem
Currently, the application uses a single, flat `TRANSFORMS` registry. This forces a redundant naming convention where score-level transforms must be prefixed with `score_` (e.g., `score_reverse`, `score_transpose`) to avoid key collisions with phrase-level transforms.

This is a "leaky abstraction" that forces the user to know internal implementation details in the JSON composition file.

## Goal
To separate transforms into two distinct registries: `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`. This will allow the same name (e.g., `reverse`) to be used in both the `phrase` and `score_transforms` blocks of a JSON composition, with the parser automatically selecting the correct implementation based on context.

## Proposed Changes

### 1. Strict Scope Taxonomy
Introduce a formal taxonomy for transform scopes using Enums to define exactly how a transform callable is executed.

```python
class PhraseScope(Enum):
    STANDARD = "standard"         # f(tones: list[Tone])
    RELATIVE = "relative"         # f(tones: list[Tone], ref_tones: list[Tone])

class ScoreScope(Enum):
    GLOBAL = "global"             # f(score: Score)
    EACH_VOICE = "each_voice"     # f(tones: list[Tone]) applied per voice
    TARGET_MOTIFS = "target_motifs" # f(score: Score, parsed_motifs: dict)
```

### 2. Unified `TransformDefinition`
Replace existing descriptor subclasses (`PhraseTransform`, `ScoreTransform`, etc.) with a single `TransformDefinition` that specifies exactly one scope.

```python
@dataclass(frozen=True)
class TransformDefinition(Generic[ScopeType]):
    name: str
    transform_func: Callable[..., Any]
    scope: ScopeType
    params_spec: TransformParamsSpec
```

### 3. Separate Registries
Replace the flat `TRANSFORMS` dictionary with two explicit registries in `transforms/registry.py`:
- `PHRASE_TRANSFORMS`: `dict[str, TransformDefinition[PhraseScope]]`
- `SCORE_TRANSFORMS`: `dict[str, TransformDefinition[ScoreScope]]`

This allows the same logical name (e.g., `reverse`) to be registered in both places with different execution scopes, while maintaining strict separation.

### 4. Parser Update
Update `composition/parser.py` to:
- Use `PHRASE_TRANSFORMS` in `_apply_phrase_transform_spec`.
- Use `SCORE_TRANSFORMS` in `_apply_score_transform_spec`.
- Dispatch the `transform_func` based on the specific `scope` value using a clean conditional block for each context.

## Discussion Outcomes & Trade-offs
- **Outcome:** We chose the two-registry approach over a unified facade to ensure maximum explicitness.
- **Pro:** Eliminates "implicit magic." Developers must intentionally register a transform for each context where it is valid.
- **Pro:** Perfectly solves the `score_` prefix naming collision by providing context-isolated lookups.
- **Con:** Slight increase in boilerplate when a transform is applicable to both phrase and score levels (it must be registered in both dictionaries).
- **Conclusion:** The trade-off is worth it for a more robust and predictable domain model.

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
