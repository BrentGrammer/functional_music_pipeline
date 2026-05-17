# Feature: Simplify Transform Definition Execution Model

## Context

A prior refactor split the flat `TRANSFORMS` registry into `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`, which cleaned up the public JSON API (no more `score_` prefixes). However, it introduced significant internal complexity that has not paid off:

- A generic `TransformDefinition[ScopeType]` with `transform_func: Callable[..., Any]`.
- `PhraseScope` and `ScoreScope` enums (`OWN_PHRASE`, `PHRASE_RELATIVE`, `EACH_VOICE`, `SCORE_AWARE`, `TARGET_MOTIFS`).
- A parser that branches on `scope` at runtime to decide how to call each transform — passing `reference_tones` for phrase-relative, `parsed_motifs` for target-motifs, looping with `apply_to_each_voice` for each-voice, and so on.

The parser knows too much about transform execution. The type model leaks `Any`. This refactor fixes both.

## Goal

The parser's transform pipeline reduces to:

```python
for definition, params in transform_pipeline:
    definition.validate_params(params)
    score = definition.apply(score, params)
```

That is the entire transform-side responsibility of `composition/parser.py`. No scope branching, no `reference_tones` plumbing, no `parsed_motifs` argument, no `apply_to_each_voice` helper, no execution-style knowledge.

The parser retains its honest job: JSON deserialization into the data model. Nothing more.

## Decision: Expand the Data Model to Match the JSON Hierarchy

The JSON composition format describes a clean compositional hierarchy. The code model only represents the top and bottom of it — `Score → Voice → Tone` — which is what forces the parser to flatten phrases away and forces every downstream complication (lifecycle-phase asymmetry, `reference_tones` plumbing, `parsed_motifs` as a special argument, mutating `each_voice` adapter).

The data model becomes a symmetric hierarchy mirroring the JSON:

```
Tone → Motif → Phrase → Voice → Score
```

Each level wraps a list of the level below. One mental model, one access pattern at each level. The JSON authoring model and the in-code data model become isomorphic.

Concretely:

- `Motif` wraps `list[Tone]` and carries its name.
- `Phrase` wraps `list[Motif]` (exact internal shape TBD when the type is designed).
- `Voice` wraps `list[Phrase]` (replacing `list[Tone]`).
- `Score` wraps `list[Voice]` (unchanged).


## Decision: Unified Transform Execution Model

With the hierarchy in place, every transform — phrase or score — has the same `apply` signature:

```python
apply(score: Score, params: Mapping[str, object]) -> Score
```

Phrase transforms are addressable inside the `Score` by their `(voice_index, phrase_index)`, which is bound at parse time so the bound `apply` matches the unified signature. The phrase/score split survives only at the public registry level (JSON placement context: phrase-level `transforms` vs. composition-level `score_transforms`) and inside registry authoring helpers. The parser sees one uniform pipeline.

Two concrete definition classes replace the generic `TransformDefinition[ScopeType]`:

```python
@dataclass(frozen=True)
class PhraseTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    apply: Callable[[Score, Mapping[str, object]], Score]

@dataclass(frozen=True)
class ScoreTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    apply: Callable[[Score, Mapping[str, object]], Score]
```

`PhraseScope` and `ScoreScope` enums are removed. "Scope" is encoded as *behavior* inside the `apply` closure, not as a runtime tag.

Raw transform functions keep their existing narrow signatures (e.g. `reverse_tones(tones)`, `phrase_feigenbaum_shrink(tones, previous_tones, **params)`, `stretto(score, motif_name, **params)`). Signature adaptation lives in registry authoring helpers that build the `apply` closure at registration time:

- `own_phrase(...)` — closes over `(voice_index, phrase_index)`, extracts that phrase's tones, calls the raw function, returns a new `Score` with the phrase replaced.
- `phrase_relative(...)` — same as above but also computes reference tones from preceding phrases in the same `Score` at apply time.
- `each_voice(...)` — iterates `score.voices`, applies the raw function per voice, returns a new `Score`.
- `score_aware(...)` — passthrough.
- `target_motifs(...)` — looks up the named motif by traversing the `Score` hierarchy and passes it to the raw function.

## Decision: Named-Entity Lookup is Hierarchy Traversal

Transforms that reference named entities (today only `stretto` with a motif name) find them by walking the data-model hierarchy on the `Score`. No separate name registry is attached to `Score`. The data model is the lookup table.

```python
# Conceptual: stretto finds its target motif by traversal.
for voice in score.voices:
    for phrase in voice.phrases:
        for motif in phrase.motifs:
            if motif.name == target_name:
                ...
```

Consequence: a motif declared in the JSON `motifs` block but never referenced by any phrase does not exist in the resulting `Score`. This is correct — unused motifs are not part of the composition.

## Decision: `validate_params` Stays Parameter-Only

`validate_params(params)` validates the params dict against the transform's parameter contract: types, shapes, ranges, allowed values. It does not take a `Score`.

Cross-reference failures (e.g. "motif name not found in score") are runtime resolution errors raised inside `apply`, not parameter contract violations.

## Decision: Mutation Discipline

Transforms return new objects. No in-place mutation of `Score`, `Voice`, `Phrase`, or `Motif`. Today's `each_voice` adapter (which mutates `score.voices[i]`) is replaced by a new-`Score`-returning version.


## Parser Shape

`composition/parser.py` does two clearly separated things:

1. **JSON deserialization** into the `Tone → Motif → Phrase → Voice → Score` hierarchy. Includes shape validation, tone-string parsing (`"440:0.5"` → `Tone`), motif/phrase/voice/score construction, motif-name resolution inside phrases, and collection of transform specs. Phrase-transform location binding (`voice_index`, `phrase_index`) happens here.
2. **Uniform transform pipeline** — the three-line loop shown in the Goal section.

## Acceptance Criteria

- `Phrase` and `Motif` types exist in `score_model/` and are used end-to-end.
- `Voice` holds `list[Phrase]`. `Voice.tones` is no longer the canonical representation.
- `PhraseScope` and `ScoreScope` enums are removed.
- Generic `TransformDefinition[ScopeType]` is removed; replaced by two concrete dataclasses.
- `transform_func: Callable[..., Any]` is removed.
- Both registries' `apply` have signature `(Score, params) -> Score`.
- Parser does not branch on execution kind; transform pipeline is lookup → `validate_params` → `apply` only.
- Registry authoring helpers (`own_phrase`, `phrase_relative`, `each_voice`, `score_aware`, `target_motifs`) own all signature adaptation; raw transform functions keep their existing narrow signatures.
- No in-place mutation of data-model objects by transforms.
- `mypy .` passes without `cast`.
- Behavior is preserved across: phrase transforms, score transforms, wrong-scope diagnostics, same-name transforms across registries, target-motif transforms (`stretto`), each-voice score transforms, phrase-relative transforms.

## Open Items

- Exact internal shape of `Phrase` and `Motif` (e.g. does `Phrase` hold `list[Motif]` directly, or `list[Tone]` plus motif provenance?). To be decided when the types are designed.
- How renderers (`wav_writer`, `midi_writer`) and score-aware transforms that currently consume `voice.tones` as a flat list relate to the new hierarchy: explicit flattening helper vs. direct phrase-aware iteration. To be decided when the rendering layer is touched.
- Sequencing of the work into reviewable chunks (data-model migration first, then registry refactor on top, or interleaved). To be decided during implementation planning.
