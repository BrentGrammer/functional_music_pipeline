# Feature: Simplify Transform Definition Execution Model

## Context
We recently refactored transform lookup from a single flat `TRANSFORMS` registry into separate `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS` registries. That refactor cleaned up the public JSON API by removing `score_` prefixes and letting JSON location imply the public transform scope:

- Phrase transforms live under phrase-level `transforms`.
- Score transforms live under composition-level `score_transforms`.

The current implementation also introduced `PhraseScope`, `ScoreScope`, and a generic `TransformDefinition[ScopeType]` so a single definition type can describe several execution styles:

- `PhraseScope.OWN_PHRASE`
- `PhraseScope.PHRASE_RELATIVE`
- `ScoreScope.EACH_VOICE`
- `ScoreScope.SCORE_AWARE`
- `ScoreScope.TARGET_MOTIFS`

This works functionally, but follow-up discussion identified that the model may now be carrying too much type machinery for the problem it solves.

## Observations

### 1. `TransformDefinition[ScopeType]` is conceptually heavy
`TransformDefinition(Generic[ScopeType])` is type-checking metadata, not normal domain inheritance. That can be confusing because Python class parentheses usually signal "inherits from this base class," while `Generic[ScopeType]` is really saying "this class is parameterized by a scope enum type."

That means a reader has to understand:

- `TypeVar`
- `Generic`
- `StrEnum` bounds
- the difference between runtime inheritance and static type metadata
- why `TransformDefinition[PhraseScope]` is not actually a phrase-specific runtime class

For this codebase, that may be more conceptual load than the benefit justifies.

### 2. The generic type still does not solve callable typing cleanly
The unified definition currently stores `transform_func` as a broad callable because the raw transform functions do not share one signature:

- own-phrase transforms take `tones`
- phrase-relative transforms take `tones` and `reference_tones`
- each-voice score transforms take `tones`
- score-aware transforms take `score`
- target-motif score transforms take `score` and `parsed_motifs`

This causes mypy pressure around `Any` return values unless the model adds more generic parameters or casts. Adding more generic parameters would make the type model even more abstract.

### 3. The parser knows too much about execution style
The parser currently looks up a definition and then dispatches based on `scope` to decide how to call the raw transform function.

That means the parser knows implementation details such as:

- phrase-relative transforms need `reference_tones`
- target-motif transforms need `parsed_motifs`
- each-voice score transforms need `apply_to_each_voice`

Ideally the parser should only know JSON placement context:

- look up phrase transforms in `PHRASE_TRANSFORMS`
- look up score transforms in `SCORE_TRANSFORMS`
- validate params
- apply the transform

The parser should not need to understand every transform execution style.

### 4. A single broad context object also feels wrong
One proposed simplification was to pass a context object to every score transform, for example `ScoreTransformContext(score, params, parsed_motifs)`.

That would make parser calls uniform, but it makes `parsed_motifs` appear to be a normal dependency of all score transforms even though only target-motif transforms such as `stretto` currently need it.

That is also a smell: it broadens the interface to make typing easier rather than reflecting the actual domain.

## Design Goal
Keep the split public registries, but simplify the internal execution model.

The parser should be as dumb as possible:

```python
definition = PHRASE_TRANSFORMS[transform_name]
definition.validate_params(transform_params)
phrase_tones = definition.apply(...)
```

```python
definition = SCORE_TRANSFORMS[transform_name]
definition.validate_params(transform_params)
score = definition.apply(...)
```

The parser should not branch on transform execution kind.

## Recommendation
Replace the generic `TransformDefinition[ScopeType]` plus runtime `scope` dispatch with executable registry adapters.

Use concrete phrase and score definition classes with uniform parser-facing `apply` methods:

```python
@dataclass(frozen=True)
class PhraseTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    apply: Callable[..., list[Tone]]
```

```python
@dataclass(frozen=True)
class ScoreTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    apply: Callable[..., Score]
```

The exact `apply` signatures should be chosen during implementation, but the important direction is:

- the parser calls a uniform method per registry context
- raw transform function signature differences are hidden by registry adapter helpers
- no `Generic[ScopeType]`
- no `Callable[..., Any]` return path
- no `cast`
- no parser dispatch over `PhraseScope` or `ScoreScope`

Registry authoring helpers should own the signature adaptation:

- `own_phrase(...)`
- `phrase_relative(...)`
- `each_voice(...)`
- `score_aware(...)`
- `target_motifs(...)`

For example, a target-motif adapter can close over the fact that it needs `parsed_motifs`, while ordinary score-aware or each-voice adapters do not expose that detail to the raw transform function.

## Why This Is Better

- **Simpler mental model:** registry entries are executable definitions, not generic containers plus scope enums.
- **Dumber parser:** parser lookup stays context-based and does not branch over execution subtypes.
- **Better type clarity:** phrase definitions return `list[Tone]`; score definitions return `Score`.
- **No casts:** mypy can follow concrete parser-facing return types.
- **Domain details live at the boundary:** transform signature differences are handled where transforms are registered, not where JSON is parsed.

## Trade-off
This will introduce small adapter helper functions in `transforms/registry.py` or a nearby module. That is acceptable if it removes generic type layering and parser dispatch complexity.

The key constraint is to avoid replacing one broad abstraction with another. In particular, do not use one oversized context object that passes `parsed_motifs` to all score transforms just because one score transform needs it.

## Acceptance Criteria

- `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS` remain the public registry split.
- Parser no longer branches on `PhraseScope` or `ScoreScope`.
- `TransformDefinition(Generic[ScopeType])` is removed.
- `transform_func: Callable[..., Any]` is removed.
- `mypy .` passes without `cast`.
- Existing behavior remains unchanged for phrase transforms, score transforms, wrong-scope diagnostics, and same-name transforms across registries.


## Planning Discussion (Refined Direction)

This section records the working state of the design discussion that followed the initial recommendation above. It is intentionally additive: the earlier framing still holds, but several specifics have been sharpened and one assumption has been reversed.

### Agreed: the parser must stop branching on execution kind

There is no remaining disagreement on this. The parser should look up a definition in the appropriate registry, call `validate_params`, and invoke a uniform `apply`. Any knowledge of how a transform is executed (`PhraseScope.OWN_PHRASE` vs. `PHRASE_RELATIVE`, `ScoreScope.SCORE_AWARE` vs. `EACH_VOICE` vs. `TARGET_MOTIFS`) leaves the parser.

### Agreed: two concrete definition classes, no `Generic[ScopeType]`

Replace `TransformDefinition(Generic[ScopeType])` with two concrete dataclasses:

- `PhraseTransformDefinition`
- `ScoreTransformDefinition`

The phrase/score split is what the public registries already express. Modeling it as two classes instead of one generic class removes `TypeVar`, `Generic`, `StrEnum` bounds, and the `Callable[..., Any]` escape hatch.

`PhraseScope` and `ScoreScope` enums are removed. The "scope" of a transform is encoded by *behavior* (the closure inside `apply`), not by a runtime tag.

### Agreed: signature adaptation belongs in registry authoring helpers

Helpers such as `own_phrase(...)`, `phrase_relative(...)`, `each_voice(...)`, `score_aware(...)`, and `target_motifs(...)` build the `apply` closure at registration time. The raw transform function keeps its tight, honest signature; the helper closes over whatever extra unpacking is needed.

### Revised: phrase definitions may take a `Score` (at the definition layer)

Initial pushback against passing the full `Score` to phrase transforms turned out to be too strong once the existing code was examined:

- `parser.py` already derives `reference_tones` from elsewhere in the score (`combined_tones if combined_tones else previous_voice_tones`, line 177).
- Phrase-relative transforms are not pure `list[Tone] -> list[Tone]` functions in practice; they already depend on cross-phrase / cross-voice context.

The system already crosses the phrase/score boundary, so making that boundary explicit at the *definition* layer is healthier than hiding it behind a `reference_tones` parameter that pretends to be flat.

The agreed distinction:

- **Definition layer (`PhraseTransformDefinition.apply`):** may take `Score` plus a phrase locator (e.g. `voice_index`, `phrase_index`, or an equivalent pointer to which phrase is being transformed). This becomes the universal phrase-context input.
- **Raw transform function layer (e.g. `phrase_feigenbaum_shrink`):** keeps its narrow signature (`tones`, optionally `reference_tones`, `**params`). The registry adapter unpacks the `Score` and calls the raw function with the inputs it actually needs.

This preserves:

- Unit-testability of raw transforms with simple tone lists (current tests in `tests/test_complexity_transforms.py`, `tests/test_geological_modulation.py` continue to work without constructing fake `Score` objects).
- A uniform parser-facing `apply` signature per registry, eliminating scope dispatch.


### Open question: how `parsed_motifs` flows into score transforms

`parsed_motifs` is composition-instance state currently passed explicitly into `_apply_score_transform_spec` and only needed by `ScoreScope.TARGET_MOTIFS` transforms (e.g. `stretto`). For a uniform `ScoreTransformDefinition.apply(score, params)` signature, three options remain on the table:

1. **Migrate `parsed_motifs` onto the `Score` object.** If motifs conceptually belong to the score, attach them there. `apply(score, params)` then stays uniform and clean. *Preferred direction pending a check of whether `Score` is the right home for motifs.*
2. **Uniform three-arg `apply(score, params, parsed_motifs)`.** Every score transform receives motifs; most ignore them. Mild "broad context" smell but tolerable.
3. **Per-kind apply signatures (target-motif takes the extra arg).** Reintroduces parser-side dispatch. Rejected.

Decision deferred until the `Score`/motif relationship is examined.

### Open question: the exact phrase-locator shape

`PhraseTransformDefinition.apply` needs to know *which* phrase inside the score it is operating on. Candidates:

- `(score, voice_index, phrase_index, params)`
- `(score, phrase_location, params)` where `PhraseLocation` is a small dataclass
- `(score, current_phrase_tones, params)` — closer to today's signature but with the score available alongside

To be settled when the parser loop is rewritten; the choice affects how cleanly the parser iterates phrases and how mutation-vs-return is handled.

### Not yet agreed: full unification into a single signature

The user's stronger proposal — that *both* registries' `apply` should take `(score, params)` and return `Score`, fully unifying phrase and score definitions — has not been adopted yet. Holding the line on two distinct `apply` shapes (one per registry class) because:

- Phrase transforms apply to a single phrase, not the whole score; the parser still iterates voices and phrases.
- Forcing every phrase definition to return an updated `Score` pushes voice/phrase iteration plumbing into 15+ phrase definitions instead of keeping it in one place in the parser.
- Two concrete classes already give us "uniform within a registry, different across registries," which is sufficient to make the parser dumb.

This remains the user's open thread and may be revisited.


### Current acceptance criteria (refined)

- `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS` remain the public registry split.
- `PhraseScope` and `ScoreScope` enums are removed.
- `TransformDefinition(Generic[ScopeType])` is removed.
- `transform_func: Callable[..., Any]` is removed.
- Parser no longer branches on execution kind; it does lookup → `validate_params` → `apply` only.
- `PhraseTransformDefinition.apply` and `ScoreTransformDefinition.apply` each have one signature, fixed at the class level.
- Raw transform functions retain their existing narrow signatures; signature adaptation lives in registry authoring helpers.
- `mypy .` passes without `cast`.
- Behavior unchanged: phrase transforms, score transforms, wrong-scope diagnostics, same-name transforms across registries, target-motif transforms (`stretto`), each-voice score transforms.

### Items still to resolve before implementation

1. Where `parsed_motifs` lives (on `Score`, or as a third `apply` argument).
2. The exact phrase-locator shape passed to `PhraseTransformDefinition.apply`.
3. Whether to fully unify phrase and score `apply` into `(score, params) -> Score` (currently rejected, but flagged as user's open concern).

