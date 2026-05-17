# Feature: Simplify Transform Definition Execution Model

## Context

A prior refactor split the flat `TRANSFORMS` registry into `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`, which cleaned up the public JSON API (no more `score_` prefixes). However, it introduced significant internal complexity that has not paid off:

- A generic `TransformDefinition[ScopeType]` with `transform_func: Callable[..., Any]`.
- `PhraseScope` and `ScoreScope` enums (`OWN_PHRASE`, `PHRASE_RELATIVE`, `EACH_VOICE`, `SCORE_AWARE`, `TARGET_MOTIFS`).
- A parser that branches on `scope` at runtime to decide how to call each transform — passing `reference_tones` for phrase-relative, `parsed_motifs` for target-motifs, looping with `apply_to_each_voice` for each-voice, and so on.

The parser knows too much about transform execution. The type model leaks `Any`. This refactor fixes both.

## Goal

The parser's transform-side responsibility reduces to preserving placement:

- If a transform request appears inside a phrase's JSON, store that request in the matching `PhraseDefinition`.
- If a transform request appears in the composition's `score_transforms`, store that request in the `CompositionDefinition`.

The parser does not branch on transform execution style, compute `reference_tones`, pass `parsed_motifs`, call `apply_to_each_voice`, or pass phrase coordinates into transform definitions.

After parsing, a transform application pass receives the pure `Score` and the parsed `CompositionDefinition`:

```python
score, composition = parse_json(composition_document)
score = apply_phrase_requests(score, composition)
score = apply_score_requests(score, composition.score_transforms)
```

The parser retains its honest job: JSON deserialization into the data model and authoring definition, including preserving where each transform request was written. Transform execution belongs outside the parser.

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


## Decision: Keep Authoring Requests Separate From the Score Model

The important split is:

- `TransformDefinition` is global and reusable. It knows how to validate params and how to apply a transform.
- `TransformRequest` is local authoring data from the JSON: a transform name plus supplied params. It does not replace `TransformParamsSpec`; the full parameter contract stays on the transform definition.
- `CompositionDefinition` is the parsed authoring recipe. It preserves which transform requests were written on which phrase and which were written at score level.
- `Score`, `Voice`, `Phrase`, `Motif`, and `Tone` remain pure musical data. They do not store transform requests.

With the hierarchy in place, phrase transforms apply to the active phrase, with access to the full score for context when needed. Score transforms apply to the whole score. The transform application pass receives both the pure `Score` and the parsed `CompositionDefinition`, so it can preserve placement without storing authoring metadata on the score model.

Two concrete definition classes replace the generic `TransformDefinition[ScopeType]`:

```python
@dataclass(frozen=True)
class TransformRequest:
    name: str
    params: Mapping[str, object]

@dataclass(frozen=True)
class PhraseDefinition:
    transforms: list[TransformRequest]

@dataclass(frozen=True)
class VoiceDefinition:
    phrases: list[PhraseDefinition]

@dataclass(frozen=True)
class CompositionDefinition:
    voices: list[VoiceDefinition]
    score_transforms: list[TransformRequest]

@dataclass(frozen=True)
class PhraseTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    apply: Callable[[Phrase, Score, Mapping[str, object]], Phrase]

@dataclass(frozen=True)
class ScoreTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    apply: Callable[[Score, Mapping[str, object]], Score]
```

`PhraseScope` and `ScoreScope` enums are removed. "Scope" is encoded by the definition type and by where the request lives in `CompositionDefinition`, not by a runtime tag.

Raw transform functions keep their existing narrow signatures (e.g. `reverse_tones(tones)`, `phrase_feigenbaum_shrink(tones, previous_tones, **params)`, `stretto(score, motif_name, **params)`). Registry entries should prefer explicit `apply` functions over generic helper factories. Add a helper only when repeated adaptation logic becomes materially noisy; do not make helper functions a required part of the design.

Phrase-relative transforms read surrounding score context but still return one new `Phrase`. If a transform needs to rewrite multiple phrases, voices, or the whole score, it belongs in `SCORE_TRANSFORMS`.

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

`composition/parser.py` does not implement transform execution. It parses JSON into a pure `Score` plus a `CompositionDefinition` that preserves transform placement, then delegates to the transform application module.

That includes shape validation, tone-string parsing (`"440:0.5"` → `Tone`), motif/phrase/voice/score construction, motif-name resolution inside phrases, and preserving transform requests in the parallel authoring definition where they were declared.

Transform execution is moved out of the parser into a transform application module. That module walks the score and composition definition together, one hierarchy level per function:

```python
score = apply_phrase_requests(score, composition)
score = apply_score_requests(score, composition.score_transforms)
```

The traversal owns the fact that "this request belongs to this phrase." The definition does not own a phrase, and the parser does not pass phrase coordinates into `apply`.

## Acceptance Criteria

- `Phrase` and `Motif` types exist in `score_model/` and are used end-to-end.
- `Voice` holds `list[Phrase]`. `Voice.tones` is no longer the canonical representation.
- `PhraseScope` and `ScoreScope` enums are removed.
- Generic `TransformDefinition[ScopeType]` is removed; replaced by two concrete dataclasses.
- `transform_func: Callable[..., Any]` is removed.
- Phrase definitions apply with signature `(Phrase, Score, params) -> Phrase`; score definitions apply with signature `(Score, params) -> Score`.
- Parser does not branch on execution kind or call transform definitions directly; it preserves transform requests in `CompositionDefinition`.
- Transform application is a separate traversal that performs lookup → `validate_params` → `apply`.
- Registry entries prefer explicit `apply` functions; helper factories are avoided unless repeated adaptation logic becomes materially noisy.
- No `voice_index` or `phrase_index` is passed into a transform definition's public `apply`.
- No in-place mutation of data-model objects by transforms.
- `mypy .` passes without `cast`.
- Behavior is preserved across: phrase transforms, score transforms, wrong-scope diagnostics, same-name transforms across registries, target-motif transforms (`stretto`), each-voice score transforms, phrase-relative transforms.

## Resolved Design Choices

- **Internal shape:** `Phrase` wraps `list[Motif]` directly. `Motif` wraps `list[Tone]` and carries its name. No `list[Tone]`-with-provenance variant.
- **Traversal utilities are bounded.** A `score_model/traversal.py` module is permitted to hold standalone functions for genuinely shared traversals — kept minimal, kept as free functions (not methods on the data types). The default is to traverse the hierarchy directly at the call site. A new utility is added only when the same operation is needed in three or more call sites, and even then only after considering whether inlining is clearer. Tests use the same module — no separate test-only helper module. See the implementation plan's standing rules for the concrete scope during this refactor.
- **Sequencing:** the implementation is decomposed into many small, individually reviewable steps designed for a lower-powered implementing model. No big-bang migration. See the Implementation Plan section below.
- **Backward compatibility:** this is a breaking migration. Old behavior, old types, and old JSON shapes do not need to be preserved.
- **Transform boundaries:** transforms operate on `Phrase`, `Voice`, or `Score`. Transforms never operate on `Motif`. Motifs are immutable source material — pure building blocks supplied by the JSON. When a phrase transform produces a new tone sequence, the output `Phrase` contains a single new `Motif` holding those tones; the input motif structure does not survive sequence-reshaping transforms, which is the honest representation (the original motif names referred to the input partitioning, not to the transformed result). Transforms that wanted to produce multiple motifs in their output could, but none of today's phrase transforms do — they all produce one continuous tone sequence.

## Implementation Plan

The plan is decomposed into small steps. Each step changes one well-defined thing, leaves the codebase in a working state (tests passing), and has a clear "done" signal so progress can be reviewed independently. Steps are tagged for the model that should perform them:

- **(low)** — mechanical or narrowly-scoped change a lower-powered model can perform safely with the instructions given.
- **(high)** — involves semantic change, design judgment, or coordinated edits across files that benefit from a stronger model even with precise instructions.

### Standing Rules for the Implementing Model

- Do not modify `compositions/**/*.json` or any transform public names in this refactor unless a step explicitly says to.
- After every step, run `mypy .` and the test command listed in the step's done signal. If either fails, stop and report — do not improvise beyond the step's scope.
- During sub-steps 3c–3i, migrate only the consumer named in that step. Other consumers continue using the legacy helper until their own step.
- When a step says "done signal: tests pass," it means the listed tests pass and the full suite has not regressed (run `uv run pytest tests` once at the end of the step to confirm).
- **No new helper functions unless required.** Do not introduce a new helper function (in any module) unless either: (a) the same logic is needed in three or more call sites, or (b) the step explicitly says to. Prefer inlining. If unsure, inline. Tiny one-liner wrappers around a for-loop, a `sum(...)`, or a single attribute access are exactly the bloat to avoid.
- **`score_model/traversal.py` is bounded.** It contains at most one canonical function: `iter_voice_tones(voice) -> Iterator[Tone]` (or equivalent), which yields all tones of a voice by walking `voice.phrases → phrase.motifs → motif.tones`. Do not invent additional traversal utilities (`iter_phrase_tones`, `flatten_motif`, `voice_durations`, `motif_lookup`, etc.) during this refactor. Inline anything else at the call site. If a second canonical operation genuinely needs to live in this module, raise it for review rather than adding it unilaterally.

### Phase 1 — Add new data-model types (additive only)

**Step 1 (low): Add `Motif` type.** New `score_model/motif.py`. `Motif` holds `name: str` and `tones: list[Tone]`. Mirror the style of `score_model/voice.py` (constructor, `__len__`, `__getitem__`, `__iter__` if `Voice` has it). New `tests/test_motif.py` mirroring `tests/test_voice.py`. Nothing else changes.
Done signal: `uv run pytest tests/test_motif.py` passes. `mypy .` passes.

**Step 2 (low): Add `Phrase` type.** New `score_model/phrase.py`. `Phrase` holds `motifs: list[Motif]`. Mirror the same style. New `tests/test_phrase.py`. Nothing else changes.
Done signal: `uv run pytest tests/test_phrase.py` passes. `mypy .` passes.

### Phase 2 — Migrate the data model end-to-end

Step 3 is the data-model migration. It introduces a temporary, explicitly-marked migration helper (`score_model/_migration.py::_legacy_flatten_voice_tones`) in 3a-i and removes it in 3j. This helper is a transition scaffold — distinct from the bounded `score_model/traversal.py` permitted by the standing rules. Consumers are migrated off the helper one at a time. The default is direct hierarchy traversal at the call site. The single permitted utility, `iter_voice_tones(voice)`, is created in `score_model/traversal.py` on first use, and no other traversal utility is added during this refactor.

**Step 3a-i (low): Create the migration helper module.**
- Create `score_model/_migration.py`.
- File header explicitly states this is a temporary migration scaffold that will be removed at the end of Phase 2.
- Define `_legacy_flatten_voice_tones(voice)` that returns `voice.tones` for now (one-line passthrough). The function exists so callers can be migrated to it before the `Voice` internals change.
- No other file is touched.
Done signal: `uv run pytest tests` passes (no behavior change). `mypy .` passes.

**Step 3a-ii (low): Route all `voice.tones` readers through the migration helper.**
- Mechanically rewrite every read of `voice.tones`, every `for tone in voice:` iteration, every `len(voice)`, and every `voice[i]` indexing across production files and tests to use `_legacy_flatten_voice_tones(voice)` for tones (e.g. `for tone in _legacy_flatten_voice_tones(voice):`). For `len(voice)` and `voice[i]`, keep them as-is; they will be reviewed in 3a-iii.
- Files to check: `audio_rendering/wav_writer.py`, `midi_rendering/midi_writer.py`, `transforms/geological/frost_effect.py`, `transforms/counterpoint/fugue.py`, `transforms/proportion/feigenbaum.py`, `composition/parser.py`, all files in `tests/`.
- Use `rg "voice\.tones|for tone in voice|len\(voice\)|voice\["` to find call sites. Do not skip any.
- Do not change `Voice` itself yet.
Done signal: `uv run pytest tests` passes (no behavior change). `mypy .` passes. `rg "voice\.tones" --type py` returns only the implementation inside `_legacy_flatten_voice_tones`.

**Step 3a-iii (high): Change `Voice` to hold `phrases: list[Phrase]`.**
- `Voice.__init__` now accepts `phrases: list[Phrase] | None = None` and stores `self.phrases`.
- Decide and document `Voice.__iter__`, `__len__`, `__getitem__`: they iterate / measure / index `phrases`, not tones. This is a deliberate semantic change consistent with "voices are sequences of phrases."
- Update `_legacy_flatten_voice_tones(voice)` to traverse `voice.phrases → phrase.motifs → motif.tones` and return the concatenated tone list.
- Update the parser's voice-assembly site: where it built `Voice(tones=[...])` it now builds `Voice(phrases=[Phrase(motifs=[Motif(name="<parsed>", tones=[...])])])` — a single motif holding all flattened tones for now. Phrase transforms still flatten during voice assembly as today; phrase-relative `reference_tones` plumbing is unchanged.
- Update `tests/test_voice.py` and `tests/test_score.py` to assert against `voice.phrases` rather than `voice.tones` directly.
- All other consumers continue using `_legacy_flatten_voice_tones`.
Design note: this is the only step in Phase 2 that changes the public shape of `Voice`. Other consumers stay insulated by the helper.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 3b (high): Parser builds real motifs and phrases.**
- Parser stops collapsing all phrase tones into one motif. For each phrase in JSON, it builds one `Motif` per motif name referenced in the phrase's `motifs` list, in order. Motif names and tones come from the JSON top-level `motifs` block.
- Phrase transforms still run during voice assembly as today. Input to a phrase transform is the flattened tones of the phrase's motifs (concatenated in order). Output of a phrase transform is a flat tone list and is wrapped as `Phrase(motifs=[Motif(name="<transformed>", tones=result)])` — the synthetic-motif decision applied. The previous motif structure does not survive a phrase transform.
- Renderers and score-aware transforms still use `_legacy_flatten_voice_tones`.
- This step touches only `composition/parser.py` and possibly `composition/schema.py`. Do not modify JSON files. Do not touch transform implementations.
Done signal: `uv run pytest tests` passes. Every existing composition renders identically. `mypy .` passes.

For each consumer-migration sub-step below (3c–3g), replace `_legacy_flatten_voice_tones` calls with direct hierarchy traversal at the call site. The one exception: if a consumer needs the flat tone stream of a whole voice, use the canonical `iter_voice_tones(voice)` utility in `score_model/traversal.py` (create the module on first use with that one function, and only that function). Do not introduce additional traversal utilities. Inline everything else at the call site. See the standing "No new helper functions unless required" rule.

**Step 3c (low): Migrate `wav_writer`.** `audio_rendering/wav_writer.py` only. Done signal: `uv run pytest tests/test_audio_io.py` passes. `mypy .` passes.

**Step 3d (low): Migrate `midi_writer`.** `midi_rendering/midi_writer.py` only. Done signal: `uv run pytest tests/test_midi_writer.py` passes. `mypy .` passes.

**Step 3e (low): Migrate `frost_effect`.** `transforms/geological/frost_effect.py` only. Done signal: `uv run pytest tests/test_frost_effect_demo.py tests/test_frost_effect_edge_expansion.py tests/test_frost_effect_recursive_demo.py tests/test_frost_helpers.py` passes. `mypy .` passes.

**Step 3f (low): Migrate `add_pedal_tone`.** `transforms/counterpoint/fugue.py`, the `add_pedal_tone` function only. Do not touch `stretto` in this step. Done signal: `uv run pytest tests/test_counterpoint_fugue.py` passes. `mypy .` passes.

**Step 3g (low): Migrate `score_feigenbaum_sequence`.** `transforms/proportion/feigenbaum.py`, `score_feigenbaum_sequence` function only. Other functions in that file are phrase-level and untouched here. Done signal: `uv run pytest tests/test_proportion_feigenbaum.py` passes. `mypy .` passes.

**Step 3h-i (low): Prepare each-voice score transform adaptation.** Move the each-voice adaptation out of parser ownership. The adaptation gathers the voice's flat tones using `iter_voice_tones(voice)` from `score_model/traversal.py`, applies the raw transform, and constructs a new `Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=result)])])` for the result. Do not add any other helper. Done signal: `uv run pytest tests/test_parser_helpers.py tests/test_json_parser.py` passes. `mypy .` passes.

**Step 3h-ii (high): Migrate `stretto` and remove `parsed_motifs` from the score-transform path.**
- `stretto` in `transforms/counterpoint/fugue.py` is rewritten to look up its target motif by inlining the traversal of the `Score` hierarchy (`for voice in score.voices: for phrase in voice.phrases: for motif in phrase.motifs: ...`), comparing `motif.name` to the `motif` parameter. If found, it copies that motif's tones; if not found, it raises with a clear error message naming the requested motif. Inline the traversal directly in `stretto`; do not extract a motif-lookup helper. (No other transform in the codebase needs this lookup today.)
- The `parsed_motifs` argument is removed from `_apply_score_transform_spec` in `composition/parser.py` and from the call site in `parse_composition`. The `parse_motifs` function may stay as parser-internal scaffolding for now if needed for phrase construction; it is removed from any score-transform call path.
- Update `tests/test_counterpoint_fugue.py` and any related tests so the target motif is present in the score via a phrase that references it. If a test previously injected motifs via a side channel, it is rewritten to put them in the score's hierarchy where the new lookup can find them.
Design note: after this step, no transform in the codebase receives motifs out-of-band.
Done signal: `uv run pytest tests/test_counterpoint_fugue.py tests/test_json_parser.py tests/test_parser.py` passes. `mypy .` passes.

**Step 3i (low): Migrate tests.** Update every test file that still reads through `_legacy_flatten_voice_tones` to use direct hierarchy traversal at the assertion site. Use `iter_voice_tones(voice)` only where the test genuinely needs the full flat tone stream of a voice. Do not add any test-only helpers. Use `rg "_legacy_flatten_voice_tones" tests/` to find call sites. Done signal: `rg "_legacy_flatten_voice_tones" tests/` returns nothing. `uv run pytest tests` passes. `mypy .` passes.

**Step 3j (low): Delete the migration helper.**
- Remove `score_model/_migration.py`.
- Remove all remaining imports of `_legacy_flatten_voice_tones` from production code.
- Use `rg "_legacy_flatten_voice_tones"` repo-wide to confirm zero results.
Done signal: `rg "_legacy_flatten_voice_tones"` returns nothing. `uv run pytest tests` passes. `mypy .` passes.

### Phase 3 — Refactor the transform definition model

**Step 4 (low): Add transform request and new definition dataclasses.**
- Add a parsed composition-definition module with `TransformRequest`, `PhraseDefinition`, `VoiceDefinition`, and `CompositionDefinition`. `TransformRequest` has fields `name: str` and `params: Mapping[str, object]`.
- These definition classes are authoring metadata only. Do not add transform request fields to `Score`, `Voice`, `Phrase`, `Motif`, or `Tone`.
- In `transforms/base.py`, add `PhraseTransformDefinition` and `ScoreTransformDefinition`.
- `PhraseTransformDefinition` has fields `name: str`, `params_spec: TransformParamsSpec`, and `apply: Callable[[Phrase, Score, Mapping[str, object]], Phrase]`.
- `ScoreTransformDefinition` has fields `name: str`, `params_spec: TransformParamsSpec`, and `apply: Callable[[Score, Mapping[str, object]], Score]`.
- Extract the existing `TransformDefinition.validate_params` method body into a module-level free function `validate_transform_params(params_spec: TransformParamsSpec, name: str, params: Mapping[str, object]) -> None`. Both new dataclasses expose a `validate_params(self, params)` method that simply calls the free function with `self.params_spec` and `self.name`. Do not duplicate the validation logic across the two classes.
- The existing `TransformDefinition[ScopeType]` is left alone in this step; the new types are not yet wired in anywhere.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 5 (low): Add explicit apply functions.**
- Add explicit phrase and score apply functions near registry authoring code. Each function adapts one raw transform family to the new definition signature.
- Do not add generic helper factories such as `own_phrase(...)`, `phrase_relative(...)`, `each_voice(...)`, `score_aware(...)`, or `target_motifs(...)` as part of the design.
- If a small private helper is needed to avoid real duplication inside one module, keep it local and narrow. Do not create a broad registry-helper abstraction.
- Add focused tests for representative explicit apply functions: one plain phrase transform, one phrase-relative transform, one each-voice score transform, one score-aware transform, and one target-motif transform.
Done signal: focused apply-function tests and `uv run pytest tests` pass. `mypy .` passes.

**Step 6 (high): Move phrase transform application timing.**

This step changes *when* phrase transforms execute and where transform placement is stored. Today phrase transforms run during voice assembly (inside the parser's voice loop). After this step, the parser builds a pure `Score` plus a parallel `CompositionDefinition`, and phrase transforms run in a separate traversal after the `Score` is fully built. Behavior must be preserved exactly.

The change has four parts that move together:

1. **Add composition-definition storage.** Build `CompositionDefinition` as a parallel authoring tree with `VoiceDefinition`, `PhraseDefinition`, and score-level transform requests.
2. **Parse-time placement preservation.** As the parser walks JSON, it converts each transform object into a `TransformRequest` and stores it in the matching phrase definition or score definition.
3. **Score build without transforms.** The parser builds the full `Score` with all phrases populated from their motifs, but with no phrase transforms applied.
4. **Sequential phrase-transform application.** After the `Score` is built, a transform application function walks `score.voices` and `composition.voices` together, then walks each `voice.phrases` and `voice_definition.phrases` together. For each phrase request, it looks up the phrase transform in `PHRASE_TRANSFORMS` (still the old type at this step), computes any required context from the active `Score`, applies the transform to the active `Phrase`, and substitutes the returned `Phrase` into the rebuilt `Score`.

Ordering rule: application order is the natural hierarchy order: voices in JSON order, phrases in JSON order, transforms within each phrase in JSON order. This is the same order phrase transforms run today. Do not reorder or parallelize.

Constraints:
- Phrase transforms still use the old `TransformDefinition[PhraseScope]` and the old phrase-side branching code. Only WHEN they run changes, not HOW.
- Do not touch `transforms/registry.py` or transform implementations.

Verification: every existing composition must render identically. Add a focused regression test that exercises phrase-relative ordering — a 2-voice composition where voice 1's phrase 2 has a phrase-relative transform (reference is phrase 1 of voice 1), and voice 2's phrase 1 has a phrase-relative transform (reference is the whole of voice 1 after its transforms) — and assert the resulting tones match expected values consistent with current behavior.

Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 7a (low): Add new `PHRASE_TRANSFORMS_V2` registry alongside the old one.**
- In `transforms/registry.py`, add a new module-level dict `PHRASE_TRANSFORMS_V2: dict[str, PhraseTransformDefinition]` populated by rewriting each entry in `PHRASE_TRANSFORMS` with explicit apply functions from Step 5. Use the old `scope` values only to choose the correct explicit function during migration.
- Do not delete or modify the old `PHRASE_TRANSFORMS`. Do not touch the parser.
- Verify entry count matches and every key exists in both dicts.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 7b (low): Swap the parser to `PHRASE_TRANSFORMS_V2` and remove the old phrase-side branching.**
- Update the phrase-transform application traversal from Step 6 to look up definitions in `PHRASE_TRANSFORMS_V2` and call `definition.validate_params(request.params)` and `definition.apply(phrase, score, request.params)`.
- Delete the old phrase-side scope branching from the transform application code.
- Delete the old `PHRASE_TRANSFORMS` dict.
- Rename `PHRASE_TRANSFORMS_V2` to `PHRASE_TRANSFORMS`.
Done signal: `uv run pytest tests` passes. `mypy .` passes. `rg "PhraseScope" composition` returns no results.

**Step 8a (low): Add new `SCORE_TRANSFORMS_V2` registry alongside the old one.**
- Same pattern as 7a, for `SCORE_TRANSFORMS`. Use the old `scope` values only to choose the correct explicit apply function during migration.
- Do not delete the old `SCORE_TRANSFORMS`. Do not touch the parser.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 8b (low): Swap the parser to `SCORE_TRANSFORMS_V2` and remove the old score-side branching.**
- Update score-transform application to look up definitions in `SCORE_TRANSFORMS_V2` and call `definition.validate_params(request.params)` and `definition.apply(score, request.params)`.
- Delete the old score-side scope branching, the `apply_to_each_voice` helper if still present, and the old `SCORE_TRANSFORMS` dict.
- Rename `SCORE_TRANSFORMS_V2` to `SCORE_TRANSFORMS`.
Done signal: `uv run pytest tests` passes. `mypy .` passes. Transform application is now outside the parser and has no runtime scope branching.

**Step 9 (low): Verify parser shape and final small cleanups.**
- At this point the parser should only deserialize JSON into a pure `Score` plus `CompositionDefinition`. `apply_to_each_voice` and `parsed_motifs` plumbing should already be gone. This step is verification, not new work.
- Run `rg "apply_to_each_voice|parsed_motifs|PhraseScope|ScoreScope" composition transforms` and confirm no remaining references in active code paths (definitions in `transforms/base.py` are OK; they are removed in Step 10).
- If anything unexpected remains, stop and report; do not improvise.
Done signal: clean `rg` results in active paths. `uv run pytest tests` passes. `mypy .` passes.

**Step 10 (low): Delete dead types.**
- Delete `TransformDefinition` (the generic one), `PhraseScope`, `ScoreScope`, `ScopeType` TypeVar, related `Generic` machinery, and any unused type aliases or imports in `transforms/base.py`.
- Use `rg` repo-wide to confirm no remaining imports of these symbols.
Done signal: `rg "TransformDefinition\[|PhraseScope|ScoreScope|ScopeType"` returns no results. `uv run pytest tests` passes. `mypy .` passes.

### Phase 4 — Final sweep

**Step 11 (low): Cleanup and verification.**
- Update `.serena/memories/` for any stale references (search for `TRANSFORMS`, `PhraseScope`, `ScoreScope`, `Voice.tones`).
- Run `mypy .` and confirm it passes without any `cast` calls in the changed code paths.
- Run `uv run pytest tests` (full suite).
- `rg` repo-wide for stragglers: `TransformDefinition`, `PhraseScope`, `ScoreScope`, `apply_to_each_voice`, `parsed_motifs`, `voice.tones`, `_legacy_flatten_voice_tones`. All should return zero results in active code.
- Update any related feature docs in `features/` that reference the old model.
Done signal: all of the above clean.

## Estimated Final Shape

This is a sketch, not a specification. Exact function names and decomposition may differ as long as the parser preserves transform placement and the transform application pass owns execution.

```python
# composition/parser.py

def parse_composition(composition_document: object) -> Score:
    _validate_composition_structure(composition_document)

    motifs = [
        _parse_motif(name, tones)
        for name, tones in composition_document["motifs"].items()
    ]
    composition = composition_document["composition"]
    composition_definition = _parse_composition_definition(composition)

    score = Score(
        voices=[
            _parse_voice(voice_config, motifs)
            for voice_config in composition.get("voices", [])
        ],
    )

    score = apply_phrase_requests(score, composition_definition)
    score = apply_score_requests(score, composition_definition.score_transforms)
    return score
```

```python
# transforms/application.py

def apply_phrase_requests(score: Score, composition: CompositionDefinition) -> Score:
    transformed_score = score

    for voice_position, voice_definition in enumerate(composition.voices):
        transformed_score = apply_voice_requests(
            transformed_score,
            voice_position,
            voice_definition,
        )

    return transformed_score


def apply_voice_requests(
    score: Score,
    voice_position: int,
    voice_definition: VoiceDefinition,
) -> Score:
    transformed_score = score

    for phrase_position, phrase_definition in enumerate(voice_definition.phrases):
        phrase = transformed_score.voices[voice_position].phrases[phrase_position]
        transformed_phrase = apply_phrase_request_chain(
            transformed_score,
            phrase,
            phrase_definition.transforms,
        )
        transformed_score = replace_phrase_at(
            transformed_score,
            voice_position,
            phrase_position,
            transformed_phrase,
        )

    return transformed_score


def apply_phrase_request_chain(
    score: Score,
    phrase: Phrase,
    requests: list[TransformRequest],
) -> Phrase:
    transformed_phrase = phrase
    for request in requests:
        definition = PHRASE_TRANSFORMS[request.name]
        definition.validate_params(request.params)
        transformed_phrase = definition.apply(transformed_phrase, score, request.params)
    return transformed_phrase


def apply_score_requests(score: Score, requests: list[TransformRequest]) -> Score:
    transformed_score = score

    for request in requests:
        definition = SCORE_TRANSFORMS[request.name]
        definition.validate_params(request.params)
        transformed_score = definition.apply(transformed_score, request.params)

    return transformed_score
```

### Resolved Placement Design

The resolved design is:

- The parser knows where a transform request was written because that is JSON structure.
- The parser preserves that placement in `CompositionDefinition`, not in `Score`, `Voice`, `Phrase`, `Motif`, or `Tone`.
- The transform application pass walks the pure score and the composition definition together, so it naturally knows which request belongs to which phrase.
- `PhraseTransformDefinition` does not own a phrase and does not receive `voice_index` or `phrase_index`.
- Context-aware phrase transforms receive the active `Phrase` and the surrounding `Score`; they can derive reference material by traversing the hierarchy.

This rejects the previous options based on `apply(score, voice_index, phrase_index, params)`, `.bind(...)`, and phrase-registry factories. Those options made transform location a parser-call-site concern instead of a hierarchy concern.

### What's Gone Vs. Today

- `apply_to_each_voice` in the parser.
- `_apply_phrase_transform_spec`, `_apply_score_transform_spec`, `_apply_phrase_transform_specs` in the parser.
- All parser-side scope branching (`if scope is PhraseScope.OWN_PHRASE`, etc.).
- `parsed_motifs` threading through score transforms.
- `reference_tones` computation in the parser.
- `voice_index` / `phrase_index` arguments in transform definition APIs.

### What Stays

- JSON shape validation.
- Tone-string parsing (`_parse_tone_string`).
- Declared motifs list for phrase construction and motif-name resolution.
- Transform request shape validation (`{"name": str, "params": dict}`), returning `TransformRequest`.

## Open Items

None at the planning level.

## Note on Rules and Defaults

This document deliberately avoids hard-and-fast rules. The choices recorded here are defaults and design preferences, not laws. If during implementation a real reason emerges to deviate — a helper that genuinely simplifies the design, a structural change that pays off, a consumer that needs to operate differently — that is allowed and expected. The point of the plan is to capture the current best understanding of the direction, not to constrain future judgment.
