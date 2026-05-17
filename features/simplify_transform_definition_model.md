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
3. ~~Whether to fully unify phrase and score `apply` into `(score, params) -> Score`.~~ **Resolved: rejected for this refactor** due to the data-model finding (phrases are not addressable inside `Score`). Flagged as a future direction contingent on a separate data-model migration.
4. ~~Whether to reclassify phrase-relative transforms as score transforms.~~ **Resolved: rejected.** They emit `list[Tone]` and run during voice assembly; they are phrase transforms by the lifecycle-phase definition. The `OWN_PHRASE` vs. `PHRASE_RELATIVE` distinction is hidden inside registry helpers, not the public registry split.


### Data-model finding: phrases do not exist in `Score`

A follow-up exploration asked: "all transforms ultimately produce a new score, so could we unify every `apply` signature as `(score, params) -> Score`?" Reading `score_model/score.py` and `score_model/voice.py` made the answer concrete:

```python
class Score:
    voices: list[Voice]

class Voice:
    tones: list[Tone]
```

There is no `Phrase` type. Phrases are a JSON-authoring concept. The parser flattens them during voice assembly (`parser.py` line 179: `combined_tones.extend(phrase_tones)`). By the time a `Score` exists, phrase boundaries are gone — a `Voice` is just a flat tone list.

This is the load-bearing fact for the whole refactor.

### Reframed boundary: lifecycle phase, not scope

Given the data model above, the two registries are best understood as **two different lifecycle phases of composition parsing**, not as two scopes within one uniform model:

- `PHRASE_TRANSFORMS` run **during voice assembly**, before a `Score` exists. They consume and produce `list[Tone]` for one phrase.
- `SCORE_TRANSFORMS` run **after voice assembly**, once the `Score` has been built. They consume and produce `Score`.

This framing is sharper than "they both produce a score." It explains why their `apply` signatures cannot be unified today without either deep changes to the parser flow or a richer data model.

### Decision: do not unify `apply` to `(score, params) -> Score`

The user's stronger proposal — unify everything as `Score -> Score` — was examined again with the data model in hand. Three implementation paths were considered:

1. **Phrase transforms run after the Score is built.** Requires phrase boundaries to be addressable inside a `Voice`. Currently they are not. Would require adding a `Phrase` type, switching `Voice` to `list[Phrase]`, or tracking `(voice_index, start, end)` ranges out-of-band. That is a **data model migration**, not a transform-registry refactor, and is out of scope for this feature.
2. **Phrase transforms wrapped as `Score -> Score` closures.** Each phrase registration would close over `(voice_index, phrase_index)`. The parser still iterates phrases to build the closures, so iteration is moved, not eliminated. Each phrase application also constructs a fresh `Score`. Worse than the current design.
3. **Accept the asymmetry.** Phrase transforms produce `list[Tone]`; score transforms produce `Score`. The parser runs each in its appropriate lifecycle phase. This is what the current code does and what the refined design retains.

Option 3 is adopted. The two concrete definition classes (`PhraseTransformDefinition`, `ScoreTransformDefinition`) keep distinct `apply` signatures, one per lifecycle phase.

### Decision: do not reclassify phrase-relative transforms as score transforms

A related question asked whether `phrase_feigenbaum_shrink`, `phrase_feigenbaum_grow`, `phrase_golden_ratio_shrink`, and `phrase_golden_ratio_grow` belong in `SCORE_TRANSFORMS` because they read context outside their own phrase.

Inspection of the implementations (`transforms/proportion/feigenbaum.py`, `transforms/proportion/golden_ratio.py`) showed:

- They consume `(tones, previous_tones, **params)`. Both inputs are flat tone lists.
- They never see voices, voice indices, motifs, or the `Score` object.
- They emit `list[Tone]`, not `Score`.
- The cross-phrase reference is supplied by the parser as a precomputed flat tone list (`reference_tones = combined_tones if combined_tones else previous_voice_tones`).

By the lifecycle-phase definition above, these are phrase transforms: they run during voice assembly and produce phrase-level output. Their dependency on a precomputed reference tone list is an *input shape* concern (handled by the `phrase_relative` registry helper), not a registry-membership concern.

Promoting them to score transforms would:

- Change their return type from `list[Tone]` to `Score`, forcing them to handle voice/phrase locator plumbing they currently do not need.
- Move them out of the phrase pipeline, breaking composition with other phrase transforms like `reverse`, `transpose`, `delay`.
- Make the public JSON UX worse: users could no longer place these inside a phrase's `transforms` list.

The `OWN_PHRASE` vs. `PHRASE_RELATIVE` distinction is a private execution-shape detail, hidden inside the `own_phrase(...)` and `phrase_relative(...)` registry helpers. The parser does not need to know it. No public reclassification is required.

### Future direction (out of scope for this feature)

If `Score` were extended to preserve phrase structure — for example, `Voice = list[Phrase]` and `Phrase = list[Tone]` — then unifying `apply` to `(score, params) -> Score` for all transforms would become feasible. Phrase transforms could locate and rewrite their target phrase inside the existing `Score`. Lifecycle phases would collapse into one.

This is a real future direction that would deliver the "everything is `Score -> Score`" model cleanly. It is intentionally not pursued in this refactor because:

- It is a data-model change, not a registry change.
- It touches `score_model/`, every consumer of `Voice.tones`, serialization, and any rendering or audio export paths.
- The current refactor can ship the parser-simplification and type-clarity wins without it.

Flag for a separate feature proposal if/when phrase-level addressability inside `Score` becomes desirable for other reasons (e.g., richer score transforms that target specific phrases, UI inspection, or post-hoc phrase-aware analysis).

---

## Revised Direction: Adopt the Compositional Hierarchy in the Data Model

The "future direction" above is no longer deferred. The decision has been made to expand the scope of this refactor to include the data-model migration, because doing so removes the lifecycle-phase asymmetry that is the load-bearing reason for every remaining complication in the design.

### Observation: the data model already has a hierarchy in the JSON, but not in code

The JSON composition format describes a clean compositional hierarchy:

- A **composition** has motifs and a composition body.
- A **composition body** has voices and score-level transforms.
- A **voice** has phrases.
- A **phrase** references motifs and has phrase-level transforms.
- A **motif** is a sequence of tones.

The code model only represents the top and bottom of this hierarchy:

```python
class Score:
    voices: list[Voice]

class Voice:
    tones: list[Tone]
```

`Motif` and `Phrase` exist only as transient parse-time concepts. They are flattened away as soon as a `Voice` is built, which is what forces the lifecycle-phase split, the parser-side phrase iteration with `reference_tones` plumbing, the `each_voice` adapter that mutates voices in place, and the open question about where `parsed_motifs` belongs.

### Decision: introduce `Phrase` and `Motif` as first-class types

The data model becomes a symmetric compositional hierarchy, mirroring the JSON:

```
Tone → Motif → Phrase → Voice → Score
```

Each level wraps a list of the level below. One mental model, one access pattern at each level.

Concretely:

- `Motif` wraps `list[Tone]`.
- `Phrase` wraps `list[Motif]` (or whatever the smallest useful representation is — exact shape TBD when the type is designed).
- `Voice` wraps `list[Phrase]` instead of `list[Tone]`.
- `Score` wraps `list[Voice]` as today.

The JSON authoring model and the in-code data model become isomorphic. Compositional building blocks are real types that can be inspected, transformed, and reasoned about uniformly.

### Why this changes the registry refactor

With the hierarchy in place, every previous blocker for full `apply` unification disappears:

- Phrase transforms become addressable inside a `Score` by `(voice_index, phrase_index)`, so they can run after the `Score` is built and return a new `Score`. They no longer need a separate lifecycle phase.
- The parser stops iterating phrases to apply transforms inline. It builds the full `Score`, then runs a single pipeline of transforms.
- `phrase_relative` reference-tone computation moves out of the parser and into a registry adapter that reads the relevant phrases from the current `Score` at apply time.
- `parsed_motifs` no longer needs to be a special argument threaded through the parser. Motifs live in the data model.
- The `each_voice` adapter no longer needs to mutate; it returns a new `Score` with updated voices, consistent with every other adapter.

### Revised acceptance criteria

In addition to the criteria already listed above:

- `Phrase` and `Motif` types exist in `score_model/` and are used end-to-end.
- `Voice.tones` is no longer the canonical representation; voices are sequences of phrases.
- Both registries' `apply` have the signature `(Score, params) -> Score`. The phrase/score split survives only at the public registry level (JSON placement context) and inside registry authoring helpers; the parser sees one uniform pipeline.
- The parser does not iterate phrases to apply transforms; phrase transform location binding happens at parse time via a helper, and the resulting bound callable matches the unified `apply` signature.

### Items deferred or still open under the revised direction

The earlier open items either resolve or shift:

- ~~Where `parsed_motifs` lives.~~ Resolved: motifs are first-class types in the data model.
- ~~The exact phrase-locator shape.~~ Resolved in principle: phrase transforms are bound to `(voice_index, phrase_index)` at parse time so their `apply` signature collapses to `(Score, params) -> Score` like score transforms.
- New: the exact internal shape of `Phrase` and `Motif` (e.g. does `Phrase` hold `list[Motif]` directly, or does it hold a flattened `list[Tone]` plus motif provenance?). To be decided when the types are designed.
- New: how renderers and score-aware transforms that currently consume `voice.tones` as a flat list relate to the new hierarchy (explicit flattening helper vs. direct phrase-aware iteration). To be decided when the rendering layer is touched.
- New: mutation discipline across the new types — locked in as "transforms return new objects; no in-place mutation of `Score`, `Voice`, `Phrase`, or `Motif`."
- New: the sequencing of this work into reviewable chunks (data-model migration first, then registry refactor on top, or interleaved). To be decided during implementation planning.

### Scope note

This document originally framed the refactor as a registry-and-parser change with the data model held fixed. That framing is superseded. The refactor now includes the data-model migration to `Tone → Motif → Phrase → Voice → Score`, because that migration is what makes the parser genuinely simple and the registry model genuinely uniform.

