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
- `Phrase` wraps `list[Motif]`.
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

## Resolved Design Choices

- **Internal shape:** `Phrase` wraps `list[Motif]` directly. `Motif` wraps `list[Tone]` and carries its name. No `list[Tone]`-with-provenance variant.
- **Traversal utilities are permitted in a dedicated module.** A `score_model/traversal.py` (or similarly-named) utilities module holds common operations like flattening a phrase's motifs into a tone list, flattening a voice's phrases into a tone list, concatenating phrases across voices, and similar. These exist as standalone functions, not as methods on the data types, so the data types stay minimal. The default for consumers is to traverse the hierarchy directly using the structure they actually need; reach for the utilities when the same traversal is appearing repeatedly or when a consumer genuinely needs a flat view (e.g. renderers, which have no use for phrase boundaries). Add utilities as real needs arise rather than pre-building a full set. Tests use the same utilities — there is no separate test-only helper module.
- **Sequencing:** the implementation is decomposed into many small, individually reviewable steps designed for a lower-powered implementing model. No big-bang migration. See the Implementation Plan section below.
- **Backward compatibility:** this is a breaking migration. Old behavior, old types, and old JSON shapes do not need to be preserved.
- **Transform boundaries:** transforms operate on `Phrase`, `Voice`, or `Score`. Transforms never operate on `Motif`. Motifs are immutable source material — pure building blocks supplied by the JSON. When a phrase transform produces a new tone sequence, the output `Phrase` contains a single new `Motif` holding those tones; the input motif structure does not survive sequence-reshaping transforms, which is the honest representation (the original motif names referred to the input partitioning, not to the transformed result). Transforms that wanted to produce multiple motifs in their output could, but none of today's phrase transforms do — they all produce one continuous tone sequence.

## Implementation Plan

The plan is decomposed into small steps suitable for a lower-powered implementing model. Each step changes one well-defined thing, leaves the codebase in a working state (tests passing), and has a clear "done" signal so progress can be reviewed independently.

### Phase 1 — Add new data-model types (additive only)

**Step 1: Add `Motif` type.** New `score_model/motif.py`. `Motif` holds `name: str` and `tones: list[Tone]`. New `tests/test_motif.py` mirroring `tests/test_voice.py`. Nothing else changes.

**Step 2: Add `Phrase` type.** New `score_model/phrase.py`. `Phrase` holds `motifs: list[Motif]`. New `tests/test_phrase.py`. Nothing else changes.

### Phase 2 — Migrate the data model end-to-end

Step 3 is split into ten sub-steps. A temporary, explicitly-marked migration helper (`score_model/_migration.py::_legacy_flatten_voice_tones`) is introduced in 3a and removed in 3j. This helper is a transition scaffold — distinct from the permanent traversal utilities described in the Resolved Design Choices section. It exists to give consumers a deterministic mechanical translation during the migration, and is replaced step-by-step (sub-steps 3c–3i) with either direct hierarchy traversal or calls to the permanent traversal utilities module, whichever is appropriate per consumer.

**Rule for the implementing model:** during sub-steps 3c–3i, migrate only the consumer named in that step. Other consumers continue using the legacy helper until their own step.

**Step 3a: Change `Voice` internals only.**
- `Voice` stores `phrases: list[Phrase]`.
- Add `score_model/_migration.py` with `_legacy_flatten_voice_tones(voice)` returning the concatenated tones across all phrases and motifs. File header explicitly states it is temporary and will be removed at the end of Phase 2.
- Parser changes minimally: wherever it built `Voice(tones=[...])`, it now builds `Voice(phrases=[Phrase(motifs=[Motif(name="<parsed>", tones=[...])])])` — a single motif holding all flattened tones. Phrase transforms still flatten during voice assembly as today.
- Every consumer (renderers, score-aware transforms, tests) that previously read `voice.tones` is mechanically rewritten to call `_legacy_flatten_voice_tones(voice)`.
- Done signal: full test suite passes. No semantic change.

**Step 3b: Parser builds real motifs and phrases.**
- Parser stops collapsing all phrase tones into one motif. It builds one `Motif` per motif name referenced in the phrase's JSON `motifs` list, in order.
- Phrase transforms still run during voice assembly as today, but their output (a flat tone list) is wrapped as `Phrase(motifs=[Motif(name="<transformed>", tones=result)])` — the synthetic-motif decision applied.
- Renderers and score-aware transforms still use `_legacy_flatten_voice_tones`.
- Done signal: full test suite passes. Compositions render identically. Internal structure now matches the JSON's motif declarations.

For each consumer-migration sub-step below (3c–3g), the implementing model should: replace `_legacy_flatten_voice_tones` calls with either direct hierarchy traversal where natural, or with a call into a permanent traversal utility (creating `score_model/traversal.py` and adding the needed utility function on first use). The choice is per-consumer based on what reads most clearly. Renderers in particular are good candidates for traversal utilities since they have no use for phrase boundaries.

**Step 3c: Migrate `wav_writer`.** `audio_rendering/wav_writer.py`. Done signal: `tests/test_audio_io.py` passes.

**Step 3d: Migrate `midi_writer`.** `midi_rendering/midi_writer.py`. Done signal: `tests/test_midi_writer.py` passes.

**Step 3e: Migrate `frost_effect`.** `transforms/geological/frost_effect.py`. Done signal: frost effect tests pass.

**Step 3f: Migrate `add_pedal_tone`.** `transforms/counterpoint/fugue.py`. Done signal: counterpoint tests pass.

**Step 3g: Migrate `score_feigenbaum_sequence`.** `transforms/proportion/feigenbaum.py`. Done signal: feigenbaum tests pass.

**Step 3h: Migrate `apply_to_each_voice` and `stretto`.**
- `apply_to_each_voice` in `composition/parser.py` uses direct hierarchy traversal.
- `stretto` in `transforms/counterpoint/fugue.py` finds its target motif by walking the `Score` hierarchy (the named-lookup-by-traversal decision). The parser stops threading `parsed_motifs` into the stretto call site as part of this step or 3i — whichever is cleaner.
- Done signal: parser and stretto tests pass.

**Step 3i: Migrate tests.** All test files still reading through `_legacy_flatten_voice_tones` are updated to direct hierarchy traversal. Done signal: full test suite passes.

**Step 3j: Delete the helper.** Remove `score_model/_migration.py` and any remaining imports. Done signal: `rg _legacy_flatten_voice_tones` returns nothing; full test suite passes; `mypy .` passes.

### Phase 3 — Refactor the transform definition model

**Step 4: Add new definition dataclasses and `validate_params` helper.** Add `PhraseTransformDefinition` and `ScoreTransformDefinition` dataclasses in `transforms/base.py`. Extract `validate_params` into a module-level helper used by both. Nothing wired yet; existing `TransformDefinition[ScopeType]` still in use.

**Step 5: Add registry authoring helpers.** Add `own_phrase`, `phrase_relative`, `each_voice`, `score_aware`, `target_motifs` helpers (in `transforms/registry_helpers.py` or inline in `registry.py`). Each takes a raw transform function and returns the unified `apply: Callable[[Score, Mapping[str, object]], Score]`. Not wired yet.

**Step 6: Move phrase transform application timing.** Change the parser so phrase transforms run after the `Score` is fully built, using parse-time `(voice_index, phrase_index)` location binding. Phrase transforms still use the old definition type and old branching — only WHEN they run changes. Phrase-relative `reference_tones` computation moves to the new application site, reading from the current score state. All tests should still pass.

**Step 7: Migrate `PHRASE_TRANSFORMS` to new definitions and helpers.** Rewrite each entry in `transforms/registry.py` as a `PhraseTransformDefinition` built via `own_phrase(...)` or `phrase_relative(...)`. Parser's phrase-side dispatch becomes the three-line uniform form. Old phrase branching code in parser deleted.

**Step 8: Migrate `SCORE_TRANSFORMS` to new definitions and helpers.** Rewrite each entry as a `ScoreTransformDefinition` built via `each_voice(...)`, `score_aware(...)`, or `target_motifs(...)`. Parser's score-side dispatch becomes the three-line uniform form. Old score branching deleted.

**Step 9: Collapse the parser transform pipeline.** Parser now has one uniform three-line loop for both registries. Remove `apply_to_each_voice` helper from parser. Remove any remaining `parsed_motifs` plumbing.

**Step 10: Delete dead types.** Delete `TransformDefinition[ScopeType]`, `PhraseScope`, `ScoreScope`, the old `transform_func` field, related generic machinery, and any unused type aliases or imports.

### Phase 4 — Final sweep

**Step 11: Cleanup and verification.**
- Update `.serena/memories/` for stale references.
- Run `mypy .` (must pass without `cast`).
- Run `uv run pytest tests` (full suite).
- `rg` for stragglers: `TransformDefinition`, `PhraseScope`, `ScoreScope`, `apply_to_each_voice`, `parsed_motifs`, `voice.tones`, `_legacy_flatten_voice_tones`.
- Update any related feature docs in `features/`.

## Open Items

None at the planning level.

## Note on Rules and Defaults

This document deliberately avoids hard-and-fast rules. The choices recorded here are defaults and design preferences, not laws. If during implementation a real reason emerges to deviate — a helper that genuinely simplifies the design, a structural change that pays off, a consumer that needs to operate differently — that is allowed and expected. The point of the plan is to capture the current best understanding of the direction, not to constrain future judgment.
