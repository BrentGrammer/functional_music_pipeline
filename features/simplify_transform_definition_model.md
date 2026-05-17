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
