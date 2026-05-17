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
    OWN_PHRASE = "own_phrase"             # f(tones: list[Tone])
    PHRASE_RELATIVE = "phrase_relative"     # f(tones: list[Tone], ref_tones: list[Tone])

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

Do not split the registries more granularly by execution scope. Registry groups should mirror the public JSON placement contexts (`transforms` vs. `score_transforms`), while `PhraseScope` and `ScoreScope` should capture the more detailed execution behavior inside each transform definition. For example, `PHRASE_TRANSFORMS` can contain both `PhraseScope.OWN_PHRASE` and `PhraseScope.PHRASE_RELATIVE` definitions, and `SCORE_TRANSFORMS` can contain `ScoreScope.EACH_VOICE`, `ScoreScope.SCORE_AWARE`, and `ScoreScope.TARGET_MOTIFS` definitions.

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

## Implementation Plan

This can be implemented as a breaking migration. There is no need to preserve legacy `TRANSFORMS` behavior, accept old `score_` names, or support a hybrid fallback period.

Use Serena for symbol-level edits and reference tracing in the codebase, especially when changing class definitions, updating imports, or finding all references to a transform type. Use `rg` or direct file inspection for plain-text checks, fixture scans, and migration verification such as confirming that no JSON still uses `score_` names.

### Step 1: Add New Transform Definition Types
- In `transforms/base.py`, add `PhraseScope` and `ScoreScope` enums.
- Add `TransformDefinition[ScopeType]` with `name`, `transform_func`, `scope`, `params_spec`, and the existing `validate_params` behavior moved over from `TransformDescriptor`.
- Add type aliases for phrase and score definitions if useful, e.g. `PhraseTransformDefinition` and `ScoreTransformDefinition`.
- Keep the old descriptor classes temporarily during this step so existing imports still work while the migration is in progress.

Checkpoint:
```bash
uv run pytest tests/test_transforms_base.py
```

### Step 2: Replace Registry Authoring
- In `transforms/registry.py`, replace `TRANSFORMS` with `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`.
- Author registry entries with explicit inline `TransformDefinition(...)` calls.
- Register phrase transforms under current public names: `reverse`, `golden_ratio`, `invert`, `feigenbaum_sequence`, `transpose`, `scale`, `pad_silence`, `delay`, `repeat`, `erosion`, `drift`, phrase-relative transforms, `accelerando`, `ritardando`, `weierstrass`, `terraced_drift`, `cellular_automata`, `random_drop`.
- Register score transforms without `score_`: `feigenbaum_sequence`, `reverse`, `golden_ratio`, `invert`, `transpose`, `scale`, `delay`, `repeat`, `drift`, `weierstrass`, `terraced_drift`, `cellular_automata`, `random_drop`, plus score-only `add_pedal_tone`, `stretto`, `frost_effect`.
- Do not add score registrations for transforms that do not currently have score behavior.

Checkpoint:
- Import `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS` in a Python shell or focused test.
- Verify repeated names like `reverse` and `feigenbaum_sequence` exist in both `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`.
- Verify no key in `SCORE_TRANSFORMS` starts with `score_`.

### Step 3: Update Parser Lookup and Dispatch
- In `composition/parser.py`, import `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`; remove `TRANSFORMS`.
- Phrase parsing should look up names only in `PHRASE_TRANSFORMS`.
- Score parsing should look up names only in `SCORE_TRANSFORMS`.
- Dispatch phrase definitions by `PhraseScope.OWN_PHRASE` vs. `PhraseScope.PHRASE_RELATIVE`.
- Dispatch score definitions by `ScoreScope.EACH_VOICE`, `ScoreScope.SCORE_AWARE`, and `ScoreScope.TARGET_MOTIFS`.
- If a name is missing from the requested registry but exists in the other registry, raise a wrong-scope error like `Transform 'accelerando' is only available as a phrase transform.`
- If the name exists in both registries, use the registry implied by JSON context with no ambiguity.

Checkpoint:
```bash
uv run pytest tests/test_parser_helpers.py
```

### Step 4: Migrate Tests and Fixtures
- Update tests to import `PHRASE_TRANSFORMS`, `SCORE_TRANSFORMS`, `PhraseScope`, and `ScoreScope` instead of `TRANSFORMS` and legacy descriptor classes.
- Replace legacy descriptor subclass assertions with `TransformDefinition.scope` assertions. For example, a test that currently checks `isinstance(descriptor, EachVoiceTransform)` should become a test that checks `definition.scope is ScoreScope.EACH_VOICE`. A phrase test that currently checks `isinstance(descriptor, PhraseTransform)` should become a test that checks `definition.scope is PhraseScope.OWN_PHRASE`.
- Keep `transform_func` identity assertions only in a small number of registry wiring smoke tests where they add value and are not the main contract under test.
- Update score transform JSON in tests from `score_reverse`, `score_scale`, etc. to `reverse`, `scale`, etc.
- Replace tests that expect `"reverse"` to be rejected in `score_transforms`; it should now succeed because score `reverse` is valid.
- Keep or add tests for wrong-scope names using transforms that exist only in one transform dictionary, such as `accelerando` under `score_transforms` and `add_pedal_tone` under phrase `transforms`.
- For tests that temporarily inject a fake score transform for target-motif coverage, add it to `SCORE_TRANSFORMS` with `ScoreScope.TARGET_MOTIFS` and remove it in `finally`. Example:
```python
SCORE_TRANSFORMS["_test_score_with_motifs"] = TransformDefinition(
    name="_test_score_with_motifs",
    transform_func=capture_score_target_motifs_transform,
    scope=ScoreScope.TARGET_MOTIFS,
    params_spec=TransformParamsSpec(...),
)
try:
    parse_composition(...)
finally:
    SCORE_TRANSFORMS.pop("_test_score_with_motifs", None)
```

Checkpoint:
```bash
uv run pytest tests/test_json_parser.py tests/test_counterpoint_fugue.py tests/test_drift.py tests/test_pad_silence.py
```

### Step 5: Migrate Composition JSON
- Update all `compositions/**/*.json` score transform names that use `score_` prefixes: `score_reverse` to `reverse`, `score_transpose` to `transpose`, `score_scale` to `scale`, and so on.
- Keep names without `score_` prepended unchanged: `add_pedal_tone`, `stretto`, `frost_effect`.
- Update descriptions only when they describe the public transform name and would now be misleading given the new naming convention.

Checkpoint:
```bash
rg -n '"name": "score_' compositions tests
```

### Step 6: Remove Legacy Types and Imports
- Remove `TransformDescriptor`, `PhraseTransform`, `PhraseRelativeTransform`, `ScoreAwareTransform`, `ScoreTargetMotifsTransform`, `EachVoiceTransform`, and `TransformWithCallable` after parser/tests no longer use them.
- Ensure `TransformDefinition.validate_params` remains the single validation implementation.
- Remove any remaining `TRANSFORMS` imports or references in active code and tests.

Checkpoint:
```bash
rg -n 'TRANSFORMS|PhraseTransform|PhraseRelativeTransform|ScoreAwareTransform|ScoreTargetMotifsTransform|EachVoiceTransform|TransformWithCallable' composition transforms tests
```

### Final Verification
- Run the focused parser and registry tests after each migration stage.
- Run the full suite:
```bash
uv run pytest tests
```
- Required coverage should include same-name transforms in both registries, wrong-scope diagnostics, score `each_voice` dispatch, score-aware dispatch, target-motifs dispatch, and phrase-relative dispatch.

## Benefits
- **Improved UX:** Cleaner JSON schema for users.
- **Cleaner Domain Model:** Explicit separation between local (phrase) and global (score) effects.
- **Better API Foundation:** Simplifies dropdown population and validation for future UIs.
