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

The plan is decomposed into small steps. Each step changes one well-defined thing, leaves the codebase in a working state (tests passing), and has a clear "done" signal so progress can be reviewed independently. Steps are tagged for the model that should perform them:

- **(low)** — mechanical or narrowly-scoped change a lower-powered model can perform safely with the instructions given.
- **(high)** — involves semantic change, design judgment, or coordinated edits across files that benefit from a stronger model even with precise instructions.

### Standing Rules for the Implementing Model

- Do not modify `compositions/**/*.json` or any transform public names in this refactor unless a step explicitly says to.
- After every step, run `mypy .` and the test command listed in the step's done signal. If either fails, stop and report — do not improvise beyond the step's scope.
- During sub-steps 3c–3i, migrate only the consumer named in that step. Other consumers continue using the legacy helper until their own step.
- When a step says "done signal: tests pass," it means the listed tests pass and the full suite has not regressed (run `uv run pytest tests` once at the end of the step to confirm).

### Phase 1 — Add new data-model types (additive only)

**Step 1 (low): Add `Motif` type.** New `score_model/motif.py`. `Motif` holds `name: str` and `tones: list[Tone]`. Mirror the style of `score_model/voice.py` (constructor, `__len__`, `__getitem__`, `__iter__` if `Voice` has it). New `tests/test_motif.py` mirroring `tests/test_voice.py`. Nothing else changes.
Done signal: `uv run pytest tests/test_motif.py` passes. `mypy .` passes.

**Step 2 (low): Add `Phrase` type.** New `score_model/phrase.py`. `Phrase` holds `motifs: list[Motif]`. Mirror the same style. New `tests/test_phrase.py`. Nothing else changes.
Done signal: `uv run pytest tests/test_phrase.py` passes. `mypy .` passes.

### Phase 2 — Migrate the data model end-to-end

Step 3 is the data-model migration. It introduces a temporary, explicitly-marked migration helper (`score_model/_migration.py::_legacy_flatten_voice_tones`) in 3a-i and removes it in 3j. This helper is a transition scaffold — distinct from the permanent traversal utilities described in the Resolved Design Choices section. Consumers are migrated off the helper one at a time. Each can choose direct hierarchy traversal or a call into the permanent `score_model/traversal.py` utilities module (creating it and adding the needed utility on first use).

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

For each consumer-migration sub-step below (3c–3g), replace `_legacy_flatten_voice_tones` calls with either direct hierarchy traversal where natural, or with a call into a permanent traversal utility in `score_model/traversal.py` (create the module and add the needed function on first use). The choice is per-consumer based on what reads most clearly. Renderers are good candidates for traversal utilities since they have no use for phrase boundaries.

**Step 3c (low): Migrate `wav_writer`.** `audio_rendering/wav_writer.py` only. Done signal: `uv run pytest tests/test_audio_io.py` passes. `mypy .` passes.

**Step 3d (low): Migrate `midi_writer`.** `midi_rendering/midi_writer.py` only. Done signal: `uv run pytest tests/test_midi_writer.py` passes. `mypy .` passes.

**Step 3e (low): Migrate `frost_effect`.** `transforms/geological/frost_effect.py` only. Done signal: `uv run pytest tests/test_frost_effect_demo.py tests/test_frost_effect_edge_expansion.py tests/test_frost_effect_recursive_demo.py tests/test_frost_helpers.py` passes. `mypy .` passes.

**Step 3f (low): Migrate `add_pedal_tone`.** `transforms/counterpoint/fugue.py`, the `add_pedal_tone` function only. Do not touch `stretto` in this step. Done signal: `uv run pytest tests/test_counterpoint_fugue.py` passes. `mypy .` passes.

**Step 3g (low): Migrate `score_feigenbaum_sequence`.** `transforms/proportion/feigenbaum.py`, `score_feigenbaum_sequence` function only. Other functions in that file are phrase-level and untouched here. Done signal: `uv run pytest tests/test_proportion_feigenbaum.py` passes. `mypy .` passes.

**Step 3h-i (low): Migrate `apply_to_each_voice` in the parser.** In `composition/parser.py`, `apply_to_each_voice` walks `voice.phrases → phrase.motifs → motif.tones` to gather the voice's flat tones, applies the raw transform, and constructs a new `Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=result)])])` for the result. Use the traversal utility from `score_model/traversal.py` if appropriate. Done signal: `uv run pytest tests/test_parser_helpers.py tests/test_json_parser.py` passes. `mypy .` passes.

**Step 3h-ii (high): Migrate `stretto` and remove `parsed_motifs` from the score-transform path.**
- `stretto` in `transforms/counterpoint/fugue.py` is rewritten to look up its target motif by traversing the `Score` hierarchy (`for voice in score.voices: for phrase in voice.phrases: for motif in phrase.motifs: ...`), comparing `motif.name` to the `motif` parameter. If found, it copies that motif's tones; if not found, it raises with a clear error message naming the requested motif. Consider adding a small motif-lookup helper to `score_model/traversal.py` if the traversal reads awkwardly.
- The `parsed_motifs` argument is removed from `_apply_score_transform_spec` in `composition/parser.py` and from the call site in `parse_composition`. The `parse_motifs` function may stay as parser-internal scaffolding for now if needed for phrase construction; it is removed from any score-transform call path.
- Update `tests/test_counterpoint_fugue.py` and any related tests so the target motif is present in the score via a phrase that references it. If a test previously injected motifs via a side channel, it is rewritten to put them in the score's hierarchy where the new lookup can find them.
Design note: after this step, no transform in the codebase receives motifs out-of-band.
Done signal: `uv run pytest tests/test_counterpoint_fugue.py tests/test_json_parser.py tests/test_parser.py` passes. `mypy .` passes.

**Step 3i (low): Migrate tests.** Update every test file that still reads through `_legacy_flatten_voice_tones` to use direct hierarchy traversal or the permanent `score_model/traversal.py` utilities. Use `rg "_legacy_flatten_voice_tones" tests/` to find them. Done signal: `rg "_legacy_flatten_voice_tones" tests/` returns nothing. `uv run pytest tests` passes. `mypy .` passes.

**Step 3j (low): Delete the migration helper.**
- Remove `score_model/_migration.py`.
- Remove all remaining imports of `_legacy_flatten_voice_tones` from production code.
- Use `rg "_legacy_flatten_voice_tones"` repo-wide to confirm zero results.
Done signal: `rg "_legacy_flatten_voice_tones"` returns nothing. `uv run pytest tests` passes. `mypy .` passes.

### Phase 3 — Refactor the transform definition model

**Step 4 (low): Add new definition dataclasses and a free `validate_transform_params` function.**
- In `transforms/base.py`, add two new `@dataclass(frozen=True)` classes: `PhraseTransformDefinition` and `ScoreTransformDefinition`. Each has fields `name: str`, `params_spec: TransformParamsSpec`, and `apply: Callable[[Score, Mapping[str, object]], Score]`.
- Extract the existing `TransformDefinition.validate_params` method body into a module-level free function `validate_transform_params(params_spec: TransformParamsSpec, name: str, params: Mapping[str, object]) -> None`. Both new dataclasses expose a `validate_params(self, params)` method that simply calls the free function with `self.params_spec` and `self.name`. Do not duplicate the validation logic across the two classes.
- The existing `TransformDefinition[ScopeType]` is left alone in this step; the new types are not yet wired in anywhere.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 5 (low): Add registry authoring helpers.**
- Add a new module `transforms/registry_helpers.py` with five helper functions: `own_phrase(raw_func)`, `phrase_relative(raw_func)`, `each_voice(raw_func)`, `score_aware(raw_func)`, `target_motifs(raw_func)`.
- Each helper takes a raw transform function (with its existing narrow signature) and returns a callable matching `Callable[[Score, Mapping[str, object]], Score]`. For `own_phrase` and `phrase_relative`, the returned callable also takes `voice_index: int` and `phrase_index: int` as additional parameters bound at parse time (the call site is the parser's location-binding step, Step 6).
- Each helper must:
  - Walk the `Score` hierarchy to find the relevant tones / motif / voice.
  - Call the raw transform.
  - Build a new `Score` with the result substituted in (no mutation).
- Add a focused test file `tests/test_registry_helpers.py` that exercises each helper with a small synthetic raw function and asserts the constructed callable returns a correctly-shaped `Score`.
- Nothing in `transforms/registry.py` or `composition/parser.py` uses these helpers yet.
Design note: this is the foundation Steps 7 and 8 build on. Bugs here amplify across ~30 registry entries downstream. The user (or a higher-powered reviewer) should review this step's diff carefully before Steps 7 and 8 begin.
Done signal: `uv run pytest tests/test_registry_helpers.py tests` passes. `mypy .` passes.

**Step 6 (high): Move phrase transform application timing.**

This step changes *when* phrase transforms execute. Today they run during voice assembly (inside the parser's voice loop). After this step, they run after the `Score` is fully built. Behavior must be preserved exactly.

The change has three parts that move together:

1. **Parse-time location binding.** As the parser walks JSON, instead of applying each phrase transform inline, it collects an ordered list of `(voice_index, phrase_index, transform_name, transform_params)` tuples — one per JSON-declared phrase transform, in JSON order across all voices and phrases.
2. **Score build without transforms.** The parser builds the full `Score` with all phrases populated from their motifs, but with no phrase transforms applied.
3. **Sequential phrase-transform application.** After the `Score` is built, the parser walks the collected tuple list in order. For each tuple, it looks up the phrase transform in `PHRASE_TRANSFORMS` (still the old type at this step), computes `reference_tones` at apply time from the *current* `Score` (same rule the parser uses today: all preceding phrases in the same voice, or all tones of all preceding voices if this is the first phrase), applies the transform, and substitutes the result back into the score as a new `Phrase` at that location.

Ordering rule: application order is the JSON order of `(voice_index, phrase_index, transform_index_within_phrase)`. This is the same order phrase transforms run today. Do not reorder or parallelize.

Constraints:
- Phrase transforms still use the old `TransformDefinition[PhraseScope]` and the old phrase-side branching code. Only WHEN they run changes, not HOW.
- Do not touch `transforms/registry.py` or transform implementations.

Verification: every existing composition must render identically. Add a focused regression test that exercises phrase-relative ordering — a 2-voice composition where voice 1's phrase 2 has a phrase-relative transform (reference is phrase 1 of voice 1), and voice 2's phrase 1 has a phrase-relative transform (reference is the whole of voice 1 after its transforms) — and assert the resulting tones match expected values consistent with current behavior.

Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 7a (low): Add new `PHRASE_TRANSFORMS_V2` registry alongside the old one.**
- In `transforms/registry.py`, add a new module-level dict `PHRASE_TRANSFORMS_V2: dict[str, PhraseTransformDefinition]` populated by rewriting each entry in `PHRASE_TRANSFORMS` using the helpers from Step 5. Use `own_phrase(...)` for entries that today have `scope=PhraseScope.OWN_PHRASE` and `phrase_relative(...)` for those with `scope=PhraseScope.PHRASE_RELATIVE`.
- Do not delete or modify the old `PHRASE_TRANSFORMS`. Do not touch the parser.
- Verify entry count matches and every key exists in both dicts.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 7b (low): Swap the parser to `PHRASE_TRANSFORMS_V2` and remove the old phrase-side branching.**
- Update `composition/parser.py` phrase-transform application (Step 6's apply site) to look up definitions in `PHRASE_TRANSFORMS_V2` and call `definition.validate_params(params)` and `definition.apply(score, voice_index, phrase_index, params)` (or whichever signature was settled in Step 5 for the bound phrase-apply form).
- Delete the old phrase-side scope branching in the parser.
- Delete the old `PHRASE_TRANSFORMS` dict.
- Rename `PHRASE_TRANSFORMS_V2` to `PHRASE_TRANSFORMS`.
Done signal: `uv run pytest tests` passes. `mypy .` passes. `rg "PhraseScope" composition` returns no results.

**Step 8a (low): Add new `SCORE_TRANSFORMS_V2` registry alongside the old one.**
- Same pattern as 7a, for `SCORE_TRANSFORMS`. Use `each_voice(...)` for entries with `scope=ScoreScope.EACH_VOICE`, `score_aware(...)` for `ScoreScope.SCORE_AWARE`, and `target_motifs(...)` for `ScoreScope.TARGET_MOTIFS`.
- Do not delete the old `SCORE_TRANSFORMS`. Do not touch the parser.
Done signal: `uv run pytest tests` passes. `mypy .` passes.

**Step 8b (low): Swap the parser to `SCORE_TRANSFORMS_V2` and remove the old score-side branching.**
- Update score-transform application in `composition/parser.py` to look up definitions in `SCORE_TRANSFORMS_V2` and call `definition.validate_params(params)` and `definition.apply(score, params)`.
- Delete the old score-side scope branching, the `apply_to_each_voice` helper if still present in the parser, and the old `SCORE_TRANSFORMS` dict.
- Rename `SCORE_TRANSFORMS_V2` to `SCORE_TRANSFORMS`.
Done signal: `uv run pytest tests` passes. `mypy .` passes. The parser's transform-application loops are now both the three-line uniform form.

**Step 9 (low): Verify parser shape and final small cleanups.**
- At this point the parser should already have one uniform three-line transform-application loop per registry, and `apply_to_each_voice` and `parsed_motifs` plumbing should already be gone. This step is verification, not new work.
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

## Open Items

None at the planning level.

## Note on Rules and Defaults

This document deliberately avoids hard-and-fast rules. The choices recorded here are defaults and design preferences, not laws. If during implementation a real reason emerges to deviate — a helper that genuinely simplifies the design, a structural change that pays off, a consumer that needs to operate differently — that is allowed and expected. The point of the plan is to capture the current best understanding of the direction, not to constrain future judgment.
