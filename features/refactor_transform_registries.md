# Feature: Split Transform Registries (Phrase vs. Score)

## Problem
Currently, the application uses a single, flat `TRANSFORMS` registry. This forces a redundant naming convention where score-level transforms must be prefixed with `score_` (e.g., `score_reverse`, `score_transpose`) to avoid key collisions with phrase-level transforms.

This is a "leaky abstraction" that forces the user to know internal implementation details in the JSON composition file.

## Goal
To separate transforms into two distinct registries: `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`. This will allow the same name (e.g., `reverse`) to be used in both the `phrase` and `score_transforms` blocks of a JSON composition, with the parser automatically selecting the correct implementation based on context.

The goal is not to make every transform available in both places. Instead, the public transform identity becomes `(scope, name)`, where the scope is implied by the JSON location:
- Phrase scope: entries under a phrase's `transforms` list.
- Score scope: entries under the composition's `score_transforms` list.

This keeps the public API clean without pretending that every transform has both phrase-level and score-level semantics.

## Proposed Changes

### 1. Strict Scope Taxonomy
Introduce a formal taxonomy for transform scopes using Enums to define exactly how a transform callable is executed.

```python
class PhraseScope(Enum):
    STANDARD = "standard"         # f(tones: list[Tone])
    RELATIVE = "relative"         # f(tones: list[Tone], ref_tones: list[Tone])

class ScoreScope(Enum):
    SCORE_AWARE = "score_aware"   # f(score: Score)
    EACH_VOICE = "each_voice"     # f(tones: list[Tone]) applied per voice
    TARGET_MOTIFS = "target_motifs" # f(score: Score, parsed_motifs: dict)
```

### 2. Unified `TransformDefinition`
Replace existing descriptor subclasses (`PhraseTransform`, `ScoreAwareTransform`, etc.) with a single `TransformDefinition` that specifies exactly one scope.

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

Do not split the registries more granularly by execution scope. Registry groups should mirror the public JSON placement contexts (`transforms` vs. `score_transforms`), while `PhraseScope` and `ScoreScope` should capture the more detailed execution behavior inside each transform definition. For example, `PHRASE_TRANSFORMS` can contain both `PhraseScope.STANDARD` and `PhraseScope.RELATIVE` definitions, and `SCORE_TRANSFORMS` can contain `ScoreScope.EACH_VOICE`, `ScoreScope.SCORE_AWARE`, and `ScoreScope.TARGET_MOTIFS` definitions.

Name overlap across registries is expected and intentional:
- Names must be unique within a single registry.
- Names may repeat across `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`.
- Repeated names are resolved by JSON context, not by a global lookup.
- The parser should never ask "what is `reverse` globally?" It should ask "what is the phrase transform named `reverse`?" or "what is the score transform named `reverse`?"

Registry membership should be explicit:
- Register a transform in both registries only when both meanings are valid.
- Register phrase-only transforms only in `PHRASE_TRANSFORMS`.
- Register score-only transforms only in `SCORE_TRANSFORMS`.

Examples:
- `reverse`, `transpose`, `scale`, `delay`, `drift`, `weierstrass`, and similar tone-list transforms may appear in both registries when score scope means "apply this phrase transform to each voice."
- `phrase_feigenbaum_shrink`, `phrase_feigenbaum_grow`, `phrase_golden_ratio_shrink`, and `phrase_golden_ratio_grow` are phrase-only because they depend on phrase-relative context.
- `add_pedal_tone`, `stretto`, and `frost_effect` are score-only because they operate on whole-score structure or parsed motifs.
- `feigenbaum_sequence` can use the same public name in both registries, but the score registry should point to the score-aware implementation.

### 4. Parser Update
Update `composition/parser.py` to:
- Use `PHRASE_TRANSFORMS` in `_apply_phrase_transform_spec`.
- Use `SCORE_TRANSFORMS` in `_apply_score_transform_spec`.
- Dispatch the `transform_func` based on the specific `scope` value using a clean conditional block for each context.
- Emit scope-aware errors when a name exists in the other registry but not the requested one, e.g. `Transform 'accelerando' is only available as a phrase transform.`

## Discussion Outcomes & Trade-offs
- **Outcome:** We chose the two-registry approach over a unified facade to ensure maximum explicitness.
- **Pro:** Eliminates "implicit magic." Developers must intentionally register a transform for each context where it is valid.
- **Pro:** Perfectly solves the `score_` prefix naming collision by providing context-isolated lookups.
- **Pro:** Handles the real asymmetry in the transform model without treating phrase-only or score-only transforms as design problems.
- **Con:** Slight increase in boilerplate when a transform is applicable to both phrase and score levels (it must be registered in both dictionaries).
- **Conclusion:** The trade-off is worth it for a more robust and predictable domain model.

### Naming Policy
Transform names only need to be unique within a registry. The same string can safely mean different implementations when used in different JSON contexts.

Do:
- Use the same public name in both registries when the user-facing musical idea is the same, even if the execution scope differs.
- Remove the `score_` prefix from score-level public names once the parser uses `SCORE_TRANSFORMS`.
- Keep explicit score-only names when the concept has no phrase-level equivalent, e.g. `add_pedal_tone`, `stretto`, `frost_effect`.

Do not:
- Auto-register every phrase transform as a score transform.
- Require placeholder registrations for unsupported scopes.
- Treat missing registry membership as an error in the registry itself; it is a valid statement that the transform is not available in that scope.

Implementation can reduce duplicate registration boilerplate with small helper constructors such as `phrase(...)`, `phrase_relative(...)`, `each_voice(...)`, `score_aware(...)`, and `score_target_motifs(...)`.

## Implementation Plan

This can be implemented as a breaking migration. There is no need to preserve legacy `TRANSFORMS` behavior, accept old `score_` names, or support a hybrid fallback period.

### Phase 1: Foundation
- Add `PhraseScope` and `ScoreScope` Enums to `transforms/base.py`.
- Add the generic `TransformDefinition` class to `transforms/base.py`.
- Add helper constructors such as `phrase(...)`, `phrase_relative(...)`, `each_voice(...)`, `score_aware(...)`, and `score_target_motifs(...)` if they reduce registry boilerplate.
- *Goal:* Establish the new type system and the authoring helpers needed for the registry migration.

### Phase 2: Registry Migration
- Replace the flat `TRANSFORMS` dictionary with `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`.
- Register phrase transforms under their existing public names.
- Register score transforms without `score_` prefixes, e.g. `score_reverse` becomes `SCORE_TRANSFORMS["reverse"]`.
- Register repeated names in both registries when both contexts are valid.
- *Goal:* Make the registry structure match the final public API in one migration.

### Phase 3: Parser Adaptation
- Modify phrase transform lookup to use only `PHRASE_TRANSFORMS`.
- Modify score transform lookup to use only `SCORE_TRANSFORMS`.
- Remove all fallback logic to the legacy flat registry.
- Dispatch by `PhraseScope` or `ScoreScope` instead of descriptor subclass type.
- Add wrong-scope diagnostics when a requested name exists in the other registry.
- *Goal:* Resolve transform names by JSON context and scope-specific registry.

### Phase 4: JSON and Test Migration
- Update all `.json` files in `compositions/` to remove `score_` prefixes from score transform names.
- Update tests to use `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS` directly.
- Replace tests that expect phrase transforms to be rejected in `score_transforms` when a same-name score transform now exists.
- Add explicit tests for repeated names across registries, e.g. phrase `reverse` and score `reverse`.
- Add explicit tests for wrong-scope errors, e.g. a phrase-only transform used under `score_transforms`.
- *Goal:* Align fixtures and assertions with the final API.

### Phase 5: Cleanup
- Remove the legacy `TRANSFORMS` dictionary.
- Remove legacy classes (`PhraseTransform`, `ScoreAwareTransform` (formerly ScoreTransform), etc.) from `transforms/base.py`.
- Remove tests and docs that refer to `score_` names as the supported public API.
- *Goal:* Finalize the refactor and remove all technical debt.

## Benefits
- **Improved UX:** Cleaner JSON schema for users.
- **Cleaner Domain Model:** Explicit separation between local (phrase) and global (score) effects.
- **Better API Foundation:** Simplifies dropdown population and validation for future UIs.
