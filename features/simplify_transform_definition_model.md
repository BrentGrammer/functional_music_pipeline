# Feature: Simplify Transform Definition Execution Model

## Context

A prior refactor split the flat `TRANSFORMS` registry into `PHRASE_TRANSFORMS` and `SCORE_TRANSFORMS`, which cleaned up the public JSON API (no more `score_` prefixes). However, it introduced significant internal complexity that has not paid off:

- A generic `TransformDefinition[ScopeType]` with `transform_func: Callable[..., Any]`.
- `PhraseScope` and `ScoreScope` enums (`OWN_PHRASE`, `PHRASE_RELATIVE`, `EACH_VOICE`, `SCORE_AWARE`, `TARGET_MOTIFS`).
- A parser that branches on `scope` at runtime to decide how to call each transform — passing `reference_tones` for phrase-relative, `parsed_motifs` for target-motifs, looping with `apply_to_each_voice` for each-voice, and so on.

The parser knows too much about transform execution. The type model leaks `Any`. This refactor fixes both.

## Goal

The parser's transform-side responsibility reduces to preserving placement:

- If a transform request appears inside a phrase's JSON, store it as a `PhraseTransformRequest` with the phrase's `voice_index` and `phrase_index`.
- If a transform request appears in the JSON `score_transforms` field, store it as a `ScoreTransformRequest`.

The parser does not branch on transform execution style, compute `reference_tones`, pass `parsed_motifs`, call `apply_to_each_voice`, or pass phrase coordinates into transform definitions.

After parsing, a transform application pass receives the `Score` model and the parsed `ScorePlan`:

```python
score_plan = parse_score_plan(composition_json)
score = build_score(score_plan)
score = apply_transform_requests(score, score_plan)
```

The parser retains its honest job: JSON deserialization into the score model and score plan, including preserving where each transform request was written. Transform execution belongs outside the parser.

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

- `TransformDefinition` is global and reusable. It knows how to validate params and how to transform the input type declared by its callable signature.
- `TransformRequest` is local authoring data from the JSON: a transform name plus supplied params. It does not replace `TransformParamsSpec`; the full parameter contract stays on the transform definition. A request does not encode its target scope; `PhraseTransformRequest` and `ScoreTransformRequest` do that.
- `PhraseTransformRequest` and `ScoreTransformRequest` are parsed placement-aware requests. They keep transform application flat and predictable without storing authoring metadata on `Score`, `Voice`, `Phrase`, `Motif`, or `Tone`.
- `PreparedTransform` is a temporary execution adapter. It combines a parsed request, its transform definition, and any stored placement into one callable shape that is ready for `apply_transform_requests` to validate and apply.
- `ScorePlan` is the parsed authoring plan. It contains the resolved materials needed to build the initial `Score` plus the transform requests to apply afterward.
- `Score`, `Voice`, `Phrase`, `Motif`, and `Tone` remain musical data only. They do not store transform requests.

With the hierarchy in place, phrase transforms apply to the active phrase through an explicit `PhraseTransformContext`. The parsed `PhraseTransformRequest` stores the request's `voice_index` and `phrase_index`; `prepare_phrase_transform` uses those coordinates to create one `PreparedTransform.apply(score)` callable that, at execution time, builds `PhraseTransformContext(score=score, voice_index=voice_index, phrase_index=phrase_index)`. The phrase transform definition receives that context, so the active phrase is available as `context.phrase`, neighboring phrases are reachable through `context.score.voices[context.voice_index].phrases`, and phrases in other voices are reachable through `context.score.voices`.

This keeps placement explicit without making `Score`, `Voice`, `Phrase`, `Motif`, or `Tone` carry authoring metadata. The parser still only preserves where the request was written; the transform application pass turns that stored placement into executable context.

The parsed authoring model uses these plan/request classes:

```python
@dataclass(frozen=True)
class TransformRequest:
    name: str
    params: Mapping[str, object]

@dataclass(frozen=True)
class PhraseTransformRequest:
    voice_index: int
    phrase_index: int
    transform_request: TransformRequest

@dataclass(frozen=True)
class ScoreTransformRequest:
    transform_request: TransformRequest

@dataclass(frozen=True)
class PhrasePlan:
    motifs: list[Motif]

@dataclass(frozen=True)
class VoicePlan:
    phrases: list[PhrasePlan]
    # Currently there are no transforms at the Voice level.

@dataclass(frozen=True)
class ScorePlan:
    motifs: dict[str, Motif]
    voices: list[VoicePlan]
    phrase_transform_requests: list[PhraseTransformRequest]
    score_transform_requests: list[ScoreTransformRequest]
```

Two concrete transform definition classes replace the generic `TransformDefinition[ScopeType]`:

```python
@dataclass(frozen=True)
class PhraseTransformContext:
    score: Score
    voice_index: int
    phrase_index: int

    @property
    def phrase(self) -> Phrase:
        return self.score.voices[self.voice_index].phrases[self.phrase_index]

@dataclass(frozen=True)
class PhraseTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    transform: Callable[[PhraseTransformContext, Mapping[str, object]], Phrase]

@dataclass(frozen=True)
class ScoreTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    transform: Callable[[Score, Mapping[str, object]], Score]
```

Prepared transforms use this class:

```python
@dataclass(frozen=True)
class PreparedTransform:
    transform_request: TransformRequest
    transform_definition: PhraseTransformDefinition | ScoreTransformDefinition
    apply: Callable[[Score], Score]
```

`PhraseScope` and `ScoreScope` enums are removed. "Scope" is encoded by the definition type and by where the request lives in `ScorePlan`, not by a runtime tag.

Definition-level `transform` means "run the reusable transform logic on the input type declared by the definition's callable signature." Prepared-transform `apply` means "apply one prepared request to the whole `Score`."

Raw transform functions keep their existing narrow signatures (e.g. `reverse_tones(tones)`, `phrase_feigenbaum_shrink(tones, previous_tones, **params)`, `stretto(score, motif_name, **params)`). Registry entries should prefer explicit `transform` functions over generic helper factories. Add a helper only when repeated adaptation logic becomes materially noisy; do not make helper functions a required part of the design.

Phrase-relative transforms read surrounding score context from `PhraseTransformContext` but still return one new `Phrase`. For existing phrase-relative raw transforms, the explicit phrase transform function derives the needed reference material from `context.score` relative to `context.voice_index` and `context.phrase_index`, then calls the narrow raw transform function. If a transform needs to rewrite multiple phrases, voices, or the whole score, it belongs in `SCORE_TRANSFORMS`.

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

Cross-reference failures (e.g. "motif name not found in score") are runtime resolution errors raised inside `transform`, not parameter contract violations.

## Decision: Mutation Discipline

Transforms return new objects. No in-place mutation of `Score`, `Voice`, `Phrase`, or `Motif`. Today's `each_voice` adapter (which mutates `score.voices[i]`) is replaced by a new-`Score`-returning version.

Because `Motif` and `Tone` contain mutable Python objects (`list[Tone]` and tone instances), score construction must avoid shared mutable state. `ScorePlan.motifs` is the parsed motif definition table, and `PhrasePlan.motifs` is the resolved motif sequence for a phrase; `build_score(score_plan)` must create fresh `Motif` instances for each phrase and fresh `Tone` instances for each motif's tones. If the same motif name is used more than once, each use gets its own `Motif` and `Tone` instances with the same frequency and duration values.


## Parser Shape

`composition/parser.py` does not implement transform execution. It parses composition JSON into a `Score` model plus a `ScorePlan` that preserves transform placement and the resolved materials needed to build the initial score, then delegates to the transform tranformation module.

That includes shape validation, tone-string parsing (`"440:0.5"` → `Tone`), top-level motif parsing, motif-name resolution inside phrases, motif/phrase/voice/score construction, and preserving transform requests in the score plan where they were declared.

Transform execution is moved out of the parser into a transform tranformation module:

```python
score = apply_transform_requests(score, score_plan)
```

The tranformation module assembles `PreparedTransform`s from the flat request lists, then uses one uniform execution loop: validate params, apply the prepared transform, and produce the next `Score`. Assembling prepared transforms uses plain list construction, not generator/yield machinery.

This keeps `PreparedTransform` intentionally. It is not a second authoring/request model and it is not stored in `ScorePlan`; it is a temporary execution adapter created while applying transforms.

## Acceptance Criteria

- `Phrase` and `Motif` types exist in `score_model/` and are used end-to-end.
- `Voice` holds `list[Phrase]`. `Voice.tones` is no longer the canonical representation.
- `PhraseScope` and `ScoreScope` enums are removed.
- Generic `TransformDefinition[ScopeType]` is removed; replaced by two concrete dataclasses.
- `transform_func: Callable[..., Any]` is removed.
- Phrase definitions transform with signature `(PhraseTransformContext, params) -> Phrase`; score definitions transform with signature `(Score, params) -> Score`.
- Parser does not branch on execution kind or call transform definitions directly; it preserves transform requests in `ScorePlan`.
- Transform application is a separate traversal that performs lookup → `validate_params` → `apply`.
- Registry entries prefer explicit `transform` functions; helper factories are avoided unless repeated adaptation logic becomes materially noisy.
- Phrase placement is passed to phrase transforms only through `PhraseTransformContext`, not as loose `voice_index` / `phrase_index` parameters.
- No in-place mutation of data-model objects by transforms.
- `mypy .` passes without `cast`.
- Behavior is preserved across: phrase transforms, score transforms, wrong-scope diagnostics, same-name transforms across registries, target-motif transforms (`stretto`), each-voice score transforms, phrase-relative transforms.

## Resolved Design Choices

- **Internal shape:** `Phrase` wraps `list[Motif]` directly. `Motif` wraps `list[Tone]` and carries its name. No `list[Tone]`-with-provenance variant.
- **Traversal utilities are bounded.** A `score_model/traversal.py` module is permitted to hold standalone functions for genuinely shared traversals — kept minimal, kept as free functions (not methods on the data types). The default is to traverse the hierarchy directly at the call site. A new utility is added only when the same operation is needed in three or more call sites, and even then only after considering whether inlining is clearer. Tests use the same module — no separate test-only helper module. See the implementation plan's standing rules for the concrete scope during this refactor.
- **Sequencing:** the implementation is decomposed into many small, individually reviewable steps designed for a lower-powered implementing model. No big-bang migration. See the Implementation Plan section below.
- **Backward compatibility:** this is a breaking migration. Old behavior, old types, and old JSON shapes do not need to be preserved.
- **Transform boundaries:** transforms operate on `Phrase`, `Voice`, or `Score`. Transforms never operate on `Motif`. Motifs are immutable source material — pure building blocks supplied by the JSON. When a phrase transform produces a new tone sequence, the output `Phrase` contains a single new `Motif` holding those tones; the input motif structure does not survive sequence-reshaping transforms, which is the honest representation (the original motif names referred to the input partitioning, not to the transformed result). Transforms that wanted to produce multiple motifs in their output could, but none of today's phrase transforms do — they all produce one continuous tone sequence.
- **Plan resolution:** `PhrasePlan.motifs` stores the resolved ordered motif sequence for that phrase. `parse_score_plan` resolves the phrase's JSON motif-name references against `ScorePlan.motifs`; `build_score` then copies those already-resolved motifs into phrase-local `Motif` objects with copied tones. The top-level `ScorePlan.motifs` table remains the parsed definition table, while `PhrasePlan.motifs` is the per-phrase resolved sequence.

## Implementation Plan

The plan is decomposed into small steps. Each step changes one well-defined thing, leaves the codebase in a working state (tests passing), and has a clear "done" signal so progress can be reviewed independently. Steps are tagged for the model that should perform them:

- **(low)** — mechanical or narrowly-scoped change a lower-powered model can perform safely with the instructions given.
- **(high)** — involves semantic change, design judgment, or coordinated edits across files that benefit from a stronger model even with precise instructions.

NOTE ON TESTING: during the migration it is okay if tests break. do not add legacy functions generally unless you have to to make the migration easier. Only run tests that you need to verify new behavior added which are targeted and scoped to test the new changes you made. Backwards compatibility is not a concern. This is a personal application that is private with no users except myself.

### Standing Rules for the Implementing Model

- Do not modify `compositions/**/*.json` or any transform public names in this refactor unless a step explicitly says to.
- After every step, run `mypy .` and the test command listed in the step's done signal. If either fails, stop and report — do not improvise beyond the step's scope.
- During sub-steps 3c–3i, migrate only the consumer named in that step. Other consumers continue using the legacy helper until their own step.
- When a step says "done signal: tests pass," it means the listed tests pass and the full suite has not regressed (run `uv run pytest tests` once at the end of the step to confirm).
- **No new helper functions unless required.** Do not introduce a new helper function (in any module) unless either: (a) the same logic is needed in three or more call sites, or (b) the step explicitly says to. Prefer inlining. If unsure, inline. Tiny one-liner wrappers around a for-loop, a `sum(...)`, or a single attribute access are exactly the bloat to avoid.
- **`score_model/traversal.py` is bounded.** It contains at most one canonical function: `flatten_voice_tones(voice) -> Iterator[Tone]` (or equivalent), which yields all tones of a voice by walking `voice.phrases → phrase.motifs → motif.tones`. Do not invent additional traversal utilities (`iter_phrase_tones`, `flatten_motif`, `voice_durations`, `motif_lookup`, etc.) during this refactor. Inline anything else at the call site. If a second canonical operation genuinely needs to live in this module, raise it for review rather than adding it unilaterally.

### Phase 1 — Add new data-model types (additive only)

**Step 1 (low): Add `Motif` type.** New `score_model/motif.py`. `Motif` holds `name: str` and `tones: list[Tone]`. Mirror the style of `score_model/voice.py` (constructor, `__len__`, `__getitem__`, `__iter__` if `Voice` has it). New `tests/test_motif.py` mirroring `tests/test_voice.py`. Nothing else changes.
Done signal: `uv run pytest tests/test_motif.py` passes. `mypy .` passes.

**Step 2 (low): Add `Phrase` type.** New `score_model/phrase.py`. `Phrase` holds `motifs: list[Motif]`. Mirror the same style. New `tests/test_phrase.py`. Nothing else changes.
Done signal: `uv run pytest tests/test_phrase.py` passes. `mypy .` passes.

### Phase 2 — Migrate the data model end-to-end

Step 3 is the data-model migration. It introduces a temporary, explicitly-marked migration helper (`score_model/_migration.py::_legacy_flatten_voice_tones`) in 3a-i and removes it in 3j. This helper is a transition scaffold — distinct from the bounded `score_model/traversal.py` permitted by the standing rules. Consumers are migrated off the helper one at a time. The default is direct hierarchy traversal at the call site. The single permitted utility, `flatten_voice_tones(voice)`, is created in `score_model/traversal.py` on first use, and no other traversal utility is added during this refactor.

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
Done signal: `uv run pytest tests` passes only for the tests relevant to the change. Every existing composition renders identically. `mypy .` passes.

For each consumer-migration sub-step below (3c–3g), replace `_legacy_flatten_voice_tones` calls with direct hierarchy traversal at the call site. The one exception: if a consumer needs the flat tone stream of a whole voice, use the canonical `flatten_voice_tones(voice)` utility in `score_model/traversal.py` (create the module on first use with that one function, and only that function). Do not introduce additional traversal utilities. Inline everything else at the call site. See the standing "No new helper functions unless required" rule.

**Step 3c (low): Update `wav_writer` to stop using the temporary voice-flattening helper.** In `audio_rendering/wav_writer.py` only, replace `_legacy_flatten_voice_tones(voice)` with the canonical whole-voice tone traversal from `score_model/traversal.py`. The WAV writer still needs a flat tone list because audio rendering plays each voice as a continuous tone stream. Done signal: `uv run pytest tests/test_audio_io.py` passes. `mypy .` passes.

**Step 3d (low): Update `midi_writer` to stop using the temporary voice-flattening helper.** In `midi_rendering/midi_writer.py` only, replace `_legacy_flatten_voice_tones(voice)` with the canonical whole-voice tone traversal from `score_model/traversal.py`. The MIDI writer still needs a flat tone sequence because MIDI events are emitted one tone at a time per voice. Done signal: `uv run pytest tests/test_midi_writer.py` passes. `mypy .` passes.

**Step 3e (low): Update `frost_effect` to stop using the temporary voice-flattening helper.** In `transforms/geological/frost_effect.py` only, replace `_legacy_flatten_voice_tones(voice)` at each call site. Use direct hierarchy traversal where the code is inspecting a specific phrase/motif shape; use the canonical whole-voice tone traversal from `score_model/traversal.py` where the transform needs the flattened tone stream of an entire voice. Done signal: `uv run pytest tests/test_frost_effect_demo.py tests/test_frost_effect_edge_expansion.py tests/test_frost_effect_recursive_demo.py tests/test_frost_helpers.py` passes. `mypy .` passes.

**Step 3f (low): Update `add_pedal_tone` to stop using the temporary voice-flattening helper.** In `transforms/counterpoint/fugue.py`, update only the `add_pedal_tone` function so it reads each voice's flat tone stream through the canonical traversal from `score_model/traversal.py`. Do not touch `stretto` in this step. Done signal: `uv run pytest tests/test_counterpoint_fugue.py` passes. `mypy .` passes.

**Step 3g (low): Update `score_feigenbaum_sequence` to stop using the temporary voice-flattening helper.** In `transforms/proportion/feigenbaum.py`, update only the `score_feigenbaum_sequence` function so it reads each voice's flat tone stream through the canonical traversal from `score_model/traversal.py`. Other functions in that file are phrase-level and untouched here. Done signal: `uv run pytest tests/test_proportion_feigenbaum.py` passes. `mypy .` passes.

**Step 3h-i (low): Prepare each-voice score transform adaptation.** Move the each-voice adaptation out of parser ownership. The adaptation gathers the voice's flat tones using `flatten_voice_tones(voice)` from `score_model/traversal.py`, applies the raw transform, and constructs a new `Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=result)])])` for the result. Do not add any other helper. Done signal: `uv run pytest tests/test_parser_helpers.py tests/test_json_parser.py` passes. `mypy .` passes.

**Step 3h-ii (high): Migrate `stretto` and remove `parsed_motifs` from the score-transform path.**
- `stretto` in `transforms/counterpoint/fugue.py` is rewritten to look up its target motif by inlining the traversal of the `Score` hierarchy (`for voice in score.voices: for phrase in voice.phrases: for motif in phrase.motifs: ...`), comparing `motif.name` to the `motif` parameter. If found, it copies that motif's tones; if not found, it raises with a clear error message naming the requested motif. Inline the traversal directly in `stretto`; do not extract a motif-lookup helper. (No other transform in the codebase needs this lookup today.)
- The `parsed_motifs` argument is removed from `_apply_score_transform_spec` in `composition/parser.py` and from the call site in `parse_composition`. The `parse_motifs` function may stay as parser-internal scaffolding for now if needed for phrase construction; it is removed from any score-transform call path.
- Update `tests/test_counterpoint_fugue.py` and any related tests so the target motif is present in the score via a phrase that references it. If a test previously injected motifs via a side channel, it is rewritten to put them in the score's hierarchy where the new lookup can find them.
Design note: after this step, no transform in the codebase receives motifs out-of-band.
Done signal: `uv run pytest tests/test_counterpoint_fugue.py tests/test_json_parser.py tests/test_parser.py` passes. `mypy .` passes.

**Step 3i (low): Migrate tests.** Update every test file that still reads through `_legacy_flatten_voice_tones` to use direct hierarchy traversal at the assertion site. Use `flatten_voice_tones(voice)` only where the test genuinely needs the full flat tone stream of a voice. Do not add any test-only helpers. Use `rg "_legacy_flatten_voice_tones" tests/` to find call sites. Done signal: `rg "_legacy_flatten_voice_tones" tests/` returns nothing. `uv run pytest tests` passes. `mypy .` passes.

**Step 3j (low): Delete the migration helper.**
- Remove `score_model/_migration.py`.
- Remove all remaining imports of `_legacy_flatten_voice_tones` from production code.
- Use `rg "_legacy_flatten_voice_tones"` repo-wide to confirm zero results.
Done signal: `rg "_legacy_flatten_voice_tones"` returns nothing. `uv run pytest tests` passes. `mypy .` passes.

### Phase 3 — Refactor the transform definition model

**Step 4 (low): Add transform request, placed requests, prepared transform, and new definition dataclasses.**
- Add a score-plan module with `TransformRequest`, `PhraseTransformRequest`, `ScoreTransformRequest`, `PhrasePlan`, `VoicePlan`, and `ScorePlan`. `TransformRequest` has fields `name: str` and `params: Mapping[str, object]`.
- `PhraseTransformRequest` has `voice_index: int`, `phrase_index: int`, and `transform_request: TransformRequest`. `ScoreTransformRequest` has `transform_request: TransformRequest`.
- `PhrasePlan` has `motifs: list[Motif]`; `VoicePlan` has `phrases: list[PhrasePlan]`; `ScorePlan` has `motifs: dict[str, Motif]`, `voices: list[VoicePlan]`, `phrase_transform_requests: list[PhraseTransformRequest]`, and `score_transform_requests: list[ScoreTransformRequest]`.
- These plan classes are authoring metadata only. Do not add transform request fields to `Score`, `Voice`, `Phrase`, `Motif`, or `Tone`.
- In `transforms/base.py`, add `PhraseTransformContext`, `PhraseTransformDefinition`, and `ScoreTransformDefinition`.
- `PhraseTransformContext` has fields `score: Score`, `voice_index: int`, and `phrase_index: int`, plus a `phrase` property that returns `score.voices[voice_index].phrases[phrase_index]`.
- `PhraseTransformDefinition` has fields `name: str`, `params_spec: TransformParamsSpec`, and `transform: Callable[[PhraseTransformContext, Mapping[str, object]], Phrase]`.
- `ScoreTransformDefinition` has fields `name: str`, `params_spec: TransformParamsSpec`, and `transform: Callable[[Score, Mapping[str, object]], Score]`.
- Add `PreparedTransform`. Each `PreparedTransform` holds `transform_request: TransformRequest`, `transform_definition: PhraseTransformDefinition | ScoreTransformDefinition`, and an `apply(score) -> Score` callable.
- Extract the existing `TransformDefinition.validate_params` method body into a module-level free function `validate_transform_params(params_spec: TransformParamsSpec, name: str, params: Mapping[str, object]) -> None`. Both new dataclasses expose a `validate_params(self, params)` method that simply calls the free function with `self.params_spec` and `self.name`. Do not duplicate the validation logic across the two classes.
- The existing `TransformDefinition[ScopeType]` is left alone in this step; the new types are not yet wired in anywhere.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 5a (low): Add representative own-phrase explicit transform function.**
- Add exactly one explicit own-phrase adapter function: `reverse_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase`.
- Put the function in `transforms/basic/reversal.py`, next to the raw `reverse_tones` function it adapts. Do not put this function in `transforms/registry.py`.
- The function is a representative implementation for the new phrase-transform API only. It is not registered yet.
- Implementation details:
  - Ignore `params`; `reverse_tones` has no params. Do not validate params here. Definition-level validation remains the responsibility of `PhraseTransformDefinition.validate_params`.
  - Read the tones from `context.phrase` by walking `context.phrase.motifs -> motif.tones` directly. Do not use `flatten_voice_tones`, because that helper is for whole `Voice` traversal.
  - Call `reverse_tones(phrase_tones)`.
  - Return `Phrase(motifs=[Motif(name="<transformed>", tones=result)])`.
- Add a focused test in a new or existing transform test module that builds a `Score`, creates a `PhraseTransformContext`, calls `reverse_phrase_transform`, and asserts the returned `Phrase` contains the reversed tones in a single `"<transformed>"` motif.
- Do not wire this into `PHRASE_TRANSFORMS`. Do not add generic helper factories. Do not add any other explicit transform functions in this step.
Done signal: focused test and `uv run pytest tests` pass. `mypy .` passes.

**Step 5b (low): Add representative phrase-relative explicit transform function.**
- Add exactly one explicit phrase-relative adapter function: `phrase_feigenbaum_shrink_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase`.
- Put the function in `transforms/proportion/feigenbaum.py`, next to the raw `phrase_feigenbaum_shrink` function it adapts. Do not put this function in `transforms/registry.py`.
- The function is a representative implementation for the new phrase-relative API only. It is not registered yet.
- Implementation details:
  - Read the current phrase tones from `context.phrase` by walking `context.phrase.motifs -> motif.tones` directly. Do not use `flatten_voice_tones`, because that helper is for whole `Voice` traversal.
  - Derive reference tones using the same semantics as the current parser flow: if `context.phrase_index > 0`, reference all earlier phrases in the same voice; otherwise reference the immediately previous voice's full tone stream when `context.voice_index > 0`; otherwise use an empty reference list and let the raw transform raise its existing no-reference error.
  - Read `dimension` from `params` with the same default as `phrase_feigenbaum_shrink`. Keep any local type narrowing minimal and local to the call; definition-level validation remains the responsibility of `PhraseTransformDefinition.validate_params`.
  - Call `phrase_feigenbaum_shrink(current_tones, reference_tones, dimension=dimension)`.
  - Return `Phrase(motifs=[Motif(name="<transformed>", tones=result)])`.
- Add a focused test that builds a score with reference material, creates a `PhraseTransformContext`, calls `phrase_feigenbaum_shrink_transform`, and asserts the returned `Phrase` contains the expected resized tones in a single `"<transformed>"` motif.
- Do not wire this into `PHRASE_TRANSFORMS`. Do not add generic helper factories. Do not add any other explicit transform functions in this step.
Done signal: focused test and `uv run pytest tests` pass. `mypy .` passes.

**Step 5c (low): Add representative each-voice score explicit transform function.**
- Add exactly one explicit each-voice score adapter function: `reverse_score_transform(score: Score, params: Mapping[str, object]) -> Score`.
- Put the function in `transforms/basic/reversal.py`, next to the raw `reverse_tones` function it adapts. Do not put this function in `transforms/registry.py`.
- The function is a representative implementation for the new score-transform API for old `ScoreScope.EACH_VOICE` entries only. It is not registered yet.
- Implementation details:
  - Ignore `params`; `reverse_tones` has no params. Do not validate params here. Definition-level validation remains the responsibility of `ScoreTransformDefinition.validate_params`.
  - Iterate `score.voices`.
  - For each voice, read the flat whole-voice tone stream with `flatten_voice_tones(voice)`.
  - Call `reverse_tones(voice_tones)`.
  - Build a new `Voice(phrases=[Phrase(motifs=[Motif(name="<transformed>", tones=result)])])` for each transformed voice.
  - Return a new `Score` containing the transformed voices. Do not mutate the input `Score`.
- Add a focused test that builds a multi-voice score, calls `reverse_score_transform`, and asserts each output voice contains its own reversed tone stream.
- Do not wire this into `SCORE_TRANSFORMS`. Do not add generic helper factories. Do not add any other explicit transform functions in this step.
Done signal: focused test and `uv run pytest tests` pass. `mypy .` passes.

**Step 5d (low): Add representative score-aware explicit transform function.**
- Add exactly one explicit score-aware adapter function: `add_pedal_tone_score_transform(score: Score, params: Mapping[str, object]) -> Score`.
- Put the function in `transforms/counterpoint/fugue.py`, next to the raw `add_pedal_tone` function it adapts. Do not put this function in `transforms/registry.py`.
- The function is a representative implementation for the new score-transform API for old `ScoreScope.SCORE_AWARE` entries only. It is not registered yet.
- Implementation details:
  - Read `frequency` from `params`. Keep any local type narrowing minimal and local to the call; definition-level validation remains the responsibility of `ScoreTransformDefinition.validate_params`.
  - Call `add_pedal_tone(score, frequency=frequency)`.
  - Return the `Score` produced by `add_pedal_tone`.
- Add a focused test that builds a score, calls `add_pedal_tone_score_transform`, and asserts the returned score has the expected appended pedal-tone voice.
- Do not wire this into `SCORE_TRANSFORMS`. Do not add generic helper factories. Do not add any other explicit transform functions in this step.
Done signal: focused test and `uv run pytest tests` pass. `mypy .` passes.

**Step 5e (low): Add representative target-motif explicit transform function.**
- Add exactly one explicit target-motif adapter function: `stretto_score_transform(score: Score, params: Mapping[str, object]) -> Score`.
- Put the function in `transforms/counterpoint/fugue.py`, next to the raw `stretto` function it adapts. Do not put this function in `transforms/registry.py`.
- The function is a representative implementation for the new score-transform API for old `ScoreScope.TARGET_MOTIFS` entries only. It is not registered yet.
- Implementation details:
  - Read `motif`, `num_times`, and `spacing` from `params`. Keep any local type narrowing minimal and local to the call; definition-level validation remains the responsibility of `ScoreTransformDefinition.validate_params`.
  - Resolve the target motif by traversing `score.voices -> voice.phrases -> phrase.motifs` and finding the first motif whose `name` matches the requested motif name.
  - If the motif is not found, raise the same kind of runtime lookup error as `stretto` raises today.
  - Call `stretto(score, motif=target_motif.name, num_times=num_times, spacing=spacing)`.
  - Return the `Score` produced by `stretto`.
- Add a focused test that builds a score containing the target motif in the hierarchy, calls `stretto_score_transform`, and asserts the returned score contains the expected generated entry voice.
- Do not wire this into `SCORE_TRANSFORMS`. Do not add generic helper factories. Do not add any other explicit transform functions in this step.
Done signal: focused test and `uv run pytest tests` pass. `mypy .` passes.

**Step 6a (high): Add `parse_score_plan` and `build_score` without switching `parse_composition`.**
- Add `parse_score_plan(composition_json) -> ScorePlan` and `build_score(score_plan) -> Score` side by side with the existing parser flow.
- `parse_score_plan` parses the top-level motif table, resolves phrase motif-name references into `PhrasePlan.motifs`, preserves voice/phrase order, and collects score transform requests. Phrase transform request collection may be stubbed as empty in this step if needed to avoid changing behavior.
- `build_score` constructs a pure `Score` from `ScorePlan` without applying transforms, creating fresh `Motif` and `Tone` instances for each phrase use.
- Do not change `parse_composition` yet. Do not move phrase transform execution yet.
- Add focused tests for `parse_score_plan` / `build_score`, including repeated motif references producing distinct `Motif` and `Tone` instances with the same frequency and duration values.
Done signal: focused tests and `uv run pytest tests` pass. `mypy .` passes.

**Step 6b (high): Collect phrase transform requests into `ScorePlan`.**
- Extend `parse_score_plan` so phrase transforms are preserved as `PhraseTransformRequest`s with `voice_index`, `phrase_index`, and `TransformRequest`.
- Collect phrase requests by walking JSON voices from first to last, phrases within each voice from first to last, and transforms within each phrase from first to last.
- Do not change `parse_composition` yet. Do not apply these requests yet.
- Add focused tests that assert the collected phrase request order and placement.
Done signal: focused tests and `uv run pytest tests` pass. `mypy .` passes.

**Step 6c (high): Add prepared-transform assembly and application using legacy definitions.**
- Add `assemble_prepared_transforms`, `prepare_phrase_transform`, `prepare_score_transform`, and `apply_transform_requests`.
- Use the existing old `TransformDefinition[PhraseScope]` / `TransformDefinition[ScoreScope]` registries and old scope-specific call logic inside the new tranformation module for now. Only the ownership and location of execution changes.
- Phrase prepared transforms build `PhraseTransformContext` from the current score plus stored placement, apply the legacy phrase transform logic, and return a new `Score` with only the target phrase replaced.
- Score prepared transforms apply the legacy score transform logic and return the next `Score`.
- Do not switch `parse_composition` yet.
Done signal: focused application tests and `uv run pytest tests` pass. `mypy .` passes.

**Step 6d (high): Switch `parse_composition` to the new parse/build/apply flow.**

This step changes *when* phrase transforms execute and where transform placement is stored. Today phrase transforms run during voice assembly (inside the parser's voice loop). After this step, the parser builds a pure `Score` model plus a `ScorePlan` with the transforms to apply to it, and phrase transforms run in a separate traversal after the `Score` is fully built. Behavior must be preserved exactly.

This step changes *when* phrase transforms execute and where transform placement is stored. Today phrase transforms run during voice assembly (inside the parser's voice loop). After this step, the parser builds a pure `Score` model plus a `ScorePlan` with the transforms to apply to it, and phrase transforms run in a separate traversal after the `Score` is fully built. Behavior must be preserved exactly.

The change has four parts that move together:

1. **Add score-plan storage.** Build `ScorePlan` as the parsed authoring plan with `motifs` for the top-level JSON `motifs` table parsed into named `Motif` objects, `voices` for the `VoicePlan` / `PhrasePlan` hierarchy where each `PhrasePlan` stores the resolved ordered `list[Motif]`, and flat request lists for phrase-level and score-level transforms.
2. **Parse-time placement preservation.** As the parser walks JSON, it converts each transform object into a `TransformRequest`. Phrase requests are appended to `ScorePlan.phrase_transform_requests` as `PhraseTransformRequest`s with their `voice_index` and `phrase_index`; score requests are appended to `ScorePlan.score_transform_requests` as `ScoreTransformRequest`s.
3. **Score build without transforms.** The parser builds the full `Score` with all phrases populated from their motifs, but with no phrase transforms applied.
4. **Sequential transform application.** After the `Score` is built, `apply_transform_requests(score, score_plan)` assembles `PreparedTransform`s from `score_plan.phrase_transform_requests` and `score_plan.score_transform_requests`. Every prepared transform is executed with the same shape: validate params, apply, and return the next `Score`.

Ordering rule: preserve the current parser execution order. Collect phrase transform requests by walking the JSON as nested loops: voices from first to last, phrases within each voice from first to last, and transforms within each phrase from first to last. Apply those phrase requests in that collected order. After all phrase requests have been applied, apply `score_transforms` from first to last as they appear in the top-level JSON. This preserves phrase-relative behavior, where later phrase transforms can depend on earlier transformed phrases or earlier completed voices. Do not reorder or parallelize.

Constraints:
- Phrase transforms still use the old `TransformDefinition[PhraseScope]` and the old phrase-side branching code. Only WHEN they run changes, not HOW.
- Do not touch `transforms/registry.py` or transform implementations.

Verification: every existing composition must render identically. Add a focused regression test that exercises phrase-relative ordering — a 2-voice composition where voice 1's phrase 2 has a phrase-relative transform (reference is phrase 1 of voice 1), and voice 2's phrase 1 has a phrase-relative transform (reference is the whole of voice 1 after its transforms) — and assert the resulting tones match expected values consistent with current behavior.

Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 7a (low): Migrate own-phrase `PHRASE_TRANSFORMS`.**
- In `transforms/registry.py`, convert old `PhraseScope.OWN_PHRASE` entries from `TransformDefinition(...)` to `PhraseTransformDefinition(...)`.
- Each `transform` function adapts one raw phrase transform to `transform(context, params) -> Phrase` by reading tones from `context.phrase`, calling the raw tone-list transform, and wrapping the returned tones in a new one-motif `Phrase`.
- Update phrase-transform application enough to call new phrase definitions for migrated entries while any remaining old phrase entries continue through the legacy path.
- Do not migrate `PhraseScope.PHRASE_RELATIVE` entries in this step.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 7b (low): Migrate phrase-relative `PHRASE_TRANSFORMS`.**
- Convert old `PhraseScope.PHRASE_RELATIVE` entries to `PhraseTransformDefinition(...)`.
- Each transform function derives reference material from `context.score` relative to `context.voice_index` and `context.phrase_index`, calls the raw phrase-relative transform, and wraps the returned tones in a new one-motif `Phrase`.
- After this step, all `PHRASE_TRANSFORMS` entries use `PhraseTransformDefinition`.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 7c (low): Remove phrase-side legacy scope branching.**
- Update phrase-transform application to assume `PHRASE_TRANSFORMS` contains only `PhraseTransformDefinition`s.
- Delete old phrase-side scope branching from the transform application code.
- Confirm `PhraseScope` is no longer referenced in active phrase application code.
Done signal: `uv run pytest tests` passes. `mypy .` passes. `rg "PhraseScope" composition transforms/registry.py` returns no results.

**Step 8a (low): Migrate each-voice `SCORE_TRANSFORMS`.**
- Convert old `ScoreScope.EACH_VOICE` entries to `ScoreTransformDefinition(...)`.
- Each transform function iterates the score's voices, reads each voice's tones, calls the raw tone-list transform, and returns a new `Score` with transformed voices.
- Update score-transform application enough to call new score definitions for migrated entries while any remaining old score entries continue through the legacy path.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 8b (low): Migrate score-aware `SCORE_TRANSFORMS`.**
- Convert old `ScoreScope.SCORE_AWARE` entries to `ScoreTransformDefinition(...)`.
- Each transform function calls the raw score transform directly with the current `Score` and params.
- Remaining old score entries continue through the legacy path.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 8c (low): Migrate target-motif `SCORE_TRANSFORMS`.**
- Convert old `ScoreScope.TARGET_MOTIFS` entries to `ScoreTransformDefinition(...)`.
- Each transform function derives the target motif by traversing the `Score` hierarchy before calling the raw transform.
- After this step, all `SCORE_TRANSFORMS` entries use `ScoreTransformDefinition`.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 8d (low): Remove score-side legacy scope branching.**
- Update score-transform application to assume `SCORE_TRANSFORMS` contains only `ScoreTransformDefinition`s.
- Delete old score-side scope branching and the `apply_to_each_voice` helper if still present.
- Confirm transform application is outside the parser and has no runtime scope branching.
Done signal: `uv run pytest tests` passes. `mypy .` passes. Transform application is now outside the parser and has no runtime scope branching.

**Step 9 (low): Verify parser shape and final small cleanups.**
- At this point the parser should only deserialize composition JSON into a pure `Score` plus `ScorePlan`. `apply_to_each_voice` and `parsed_motifs` plumbing should already be gone. This step is verification, not new work.
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

def parse_composition(composition_json: object) -> Score:
    _validate_composition_structure(composition_json)

    score_plan = parse_score_plan(composition_json)
    score = build_score(score_plan)
    return apply_transform_requests(score, score_plan)
```

```python
# composition/score_plan.py

def parse_score_plan(composition_json: object) -> ScorePlan:
    # Parses the top-level JSON motifs table, resolves phrase motif-name
    # references into PhrasePlan.motifs, and preserves voice ordering,
    # phrase transform requests, and score transform requests.
    ...


def build_score(score_plan: ScorePlan) -> Score:
    # Constructs the pure Score hierarchy by creating fresh Motif instances
    # for each phrase and fresh Tone instances for each motif's tones.
    # If the same motif name is used more than once, each use gets its own
    # Motif and Tone instances with the same frequency and duration values.
    # Does not apply transforms.
    ...
```

```python
# transforms/application.py

def assemble_prepared_transforms(score_plan: ScorePlan) -> list[PreparedTransform]:
    prepared_transforms: list[PreparedTransform] = []

    for phrase_transform_request in score_plan.phrase_transform_requests:
        prepared_transforms.append(prepare_phrase_transform(phrase_transform_request))

    for score_transform_request in score_plan.score_transform_requests:
        prepared_transforms.append(prepare_score_transform(score_transform_request))

    return prepared_transforms


def prepare_phrase_transform(
    phrase_transform_request: PhraseTransformRequest,
) -> PreparedTransform:
    transform_request = phrase_transform_request.transform_request
    transform_definition = PHRASE_TRANSFORMS[transform_request.name]
    voice_index = phrase_transform_request.voice_index
    phrase_index = phrase_transform_request.phrase_index

    def apply(score: Score) -> Score:
        context = PhraseTransformContext(score, voice_index, phrase_index)
        transformed_phrase = transform_definition.transform(context, transform_request.params)
        # Return a new Score with only the target phrase replaced.
        ...

    return PreparedTransform(transform_request, transform_definition, apply)


def prepare_score_transform(
    score_transform_request: ScoreTransformRequest,
) -> PreparedTransform:
    transform_request = score_transform_request.transform_request
    transform_definition = SCORE_TRANSFORMS[transform_request.name]
    ...


def apply_transform_requests(score: Score, score_plan: ScorePlan) -> Score:
    transformed_score = score

    for prepared_transform in assemble_prepared_transforms(score_plan):
        prepared_transform.transform_definition.validate_params(prepared_transform.transform_request.params)
        transformed_score = prepared_transform.apply(transformed_score)

    return transformed_score
```

### Resolved Placement Design

The resolved design is:

- The parser knows where a transform request was written because that is JSON structure.
- The parser preserves that placement in `ScorePlan`, not in `Score`, `Voice`, `Phrase`, `Motif`, or `Tone`.
- `ScorePlan.phrase_transform_requests` and `ScorePlan.score_transform_requests` keep prepared-transform assembly flat and ordered.
- `assemble_prepared_transforms` creates the ordered list of `PreparedTransform`s by calling `prepare_phrase_transform` once for each phrase request and `prepare_score_transform` once for each score request.
- `prepare_phrase_transform` creates one `PreparedTransform` from one `PhraseTransformRequest`; it closes over the request's `voice_index` and `phrase_index`, and the resulting `PreparedTransform.apply(score)` builds `PhraseTransformContext(score, voice_index, phrase_index)` for the current `Score` before calling the phrase transform definition.
- `prepare_score_transform` creates one `PreparedTransform` from one `ScoreTransformRequest`; its `PreparedTransform.apply(score)` calls the score transform definition with the current `Score`.
- `apply_transform_requests` uses one uniform loop: validate params, apply the prepared transform, produce the next `Score`.
- `PhraseTransformDefinition` does not own a phrase and does not receive loose `voice_index` or `phrase_index` parameters; placement lives inside `PhraseTransformContext`.
- Context-aware phrase transforms use `context.phrase`, `context.score`, `context.voice_index`, and `context.phrase_index` to inspect neighboring phrases or other voices directly.

This rejects the previous public transform-definition options based on loose coordinate arguments like `transform(score, voice_index, phrase_index, params)`, `.bind(...)`, and phrase-registry factories. `PhraseTransformContext` keeps location explicit while grouping it with the current score model instead of making the parser call transform definitions directly.

### What's Gone Vs. Today

- `apply_to_each_voice` in the parser.
- `_apply_phrase_transform_spec`, `_apply_score_transform_spec`, `_apply_phrase_transform_specs` in the parser.
- All parser-side scope branching (`if scope is PhraseScope.OWN_PHRASE`, etc.).
- `parsed_motifs` threading through score transforms.
- `reference_tones` computation in the parser.
- Loose `voice_index` / `phrase_index` arguments in transform definition APIs; phrase placement is grouped in `PhraseTransformContext` instead.

### What Stays

- JSON shape validation.
- Tone-string parsing (`_parse_tone_string`).
- Declared motifs list for phrase construction; phrase motif-name references are resolved into `PhrasePlan.motifs`.
- Transform request shape validation (`{"name": str, "params": dict}`), returning `TransformRequest`.

## Open Items

None at the planning level.

## Future Consideration: Deep Immutability

This refactor keeps the current list-based model and prevents accidental shared mutable state by creating fresh `Motif` and `Tone` instances when building the final `Score`. After this migration, revisit whether the score model should become deeply immutable — for example, by using frozen dataclasses with tuple-backed collections throughout `Tone → Motif → Phrase → Voice → Score`. That would make repeated references safe by construction and provide a stronger guardrail against unexpected in-place mutation, but it is intentionally outside the scope of this refactor.

## Note on Rules and Defaults

This document deliberately avoids hard-and-fast rules. The choices recorded here are defaults and design preferences, not laws. If during implementation a real reason emerges to deviate — a helper that genuinely simplifies the design, a structural change that pays off, a consumer that needs to operate differently — that is allowed and expected. The point of the plan is to capture the current best understanding of the direction, not to constrain future judgment.
