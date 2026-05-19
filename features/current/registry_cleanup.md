# Registry Cleanup Handoff

## Goal

Make `transforms/registry.py` a clean name-to-definition map. Registry entries should reference named adapter functions owned by the transform modules. Avoid inline lambdas that flatten phrases, narrow params, call raw transforms, and wrap `Phrase` / `Motif` objects inside the registry.

## Current State

Phrase-side adapters already extracted and wired:

- `reverse`
- `golden_ratio`
- `invert`
- `feigenbaum_sequence`
- `transpose`
- `scale`
- `pad_silence`
- `delay`
- `repeat`
- `erosion`
- `drift`
- `accelerando`
- `ritardando`

Focused tests have passed for the batches implemented so far. `mypy` has not been run after every slice.

## Remaining Phrase-Side Cleanup

### Batch 1: Phrase-relative proportional transforms

Extract these adapters out of `transforms/registry.py`:

- `phrase_feigenbaum_shrink`
- `phrase_feigenbaum_grow`
- `phrase_golden_ratio_shrink`
- `phrase_golden_ratio_grow`

Target modules:

- Put the Feigenbaum adapters in `transforms/proportion/feigenbaum.py`.
- Put the golden-ratio adapters in `transforms/proportion/golden_ratio.py`.

Adapter behavior:

- Signature: `(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase`.
- Flatten current phrase tones from `context.phrase.motifs`.
- Derive reference tones with the existing registry semantics:
  - If `context.phrase_index > 0`, use all earlier phrases in the same voice.
  - Else if `context.voice_index > 0`, use the immediately previous voice's full flattened tone stream.
  - Else use an empty list and let the raw transform raise its existing no-reference error.
- Read `dimension = params.get("dimension", ToneDimension.DURATION)`.
- Validate `dimension` is `str | ToneDimension`.
- Call the existing raw phrase-relative transform.
- Return `Phrase(motifs=[Motif(name="<transformed>", tones=result)])`.

Suggested tests:

```bash
uv run pytest tests/test_json_parser.py tests/test_transformation.py tests/test_proportion_feigenbaum.py tests/test_proportion_golden_ratio.py
```

### Batch 2: Required dimension plus secondary params

Extract these phrase adapters:

- `weierstrass`
- `terraced_drift`

Target modules:

- `transforms/complexity/weierstrass.py`
- `transforms/geological/terraced_drift.py`

Adapter behavior:

- Flatten current phrase tones from `context.phrase.motifs`.
- For `weierstrass`, validate `dimension` as `str | ToneDimension` and `intensity` as `str`.
- For `terraced_drift`, validate `dimension` as `str | ToneDimension` and `max_step_change_pct` as `int`, rejecting `bool`.
- Call the existing raw transform and wrap in a one-motif `Phrase` named `"<transformed>"`.

Suggested tests:

```bash
uv run pytest tests/test_json_parser.py tests/test_transformation.py tests/test_geological_modulation.py
```

### Batch 3: Complexity phrase transforms

Extract these phrase adapters:

- `cellular_automata`
- `random_drop`

Target modules:

- `transforms/complexity/cellular_automata.py`
- `transforms/complexity/random_drop.py`

Adapter behavior:

- Flatten current phrase tones from `context.phrase.motifs`.
- Validate `dimension` as `str | ToneDimension`.
- Validate integer params as `int`, rejecting `bool`.
- Validate float params as `int | float`, rejecting `bool`, and pass as `float`.
- Call the existing raw transform and wrap in a one-motif `Phrase` named `"<transformed>"`.

Suggested tests:

```bash
uv run pytest tests/test_json_parser.py tests/test_transformation.py
```

## Remaining Score-Side Cleanup

After phrase-side lambdas are gone, clean up `SCORE_TRANSFORMS`.

### Batch 4: Existing score-adapter cleanup

Replace simple forwarding lambdas with direct function references:

- `add_pedal_tone`: use `transform=add_pedal_tone_score_transform`
- `stretto`: use `transform=stretto_score_transform_adapter`

For `frost_effect`, add a named adapter in `transforms/geological/frost_effect.py` that validates/extracts `iterations` from `params`, calls `frost_effect(score, iterations=iterations)`, then wire the registry to that adapter.

Suggested tests:

```bash
uv run pytest tests/test_json_parser.py tests/test_counterpoint_fugue.py tests/test_frost_effect_demo.py tests/test_frost_effect_edge_expansion.py tests/test_frost_effect_recursive_demo.py tests/test_frost_helpers.py
```

### Batch 5: Score each-voice basic adapters

Extract named score adapters for:

- `invert`
- `transpose`
- `scale`
- `delay`
- `repeat`
- `drift`

Target modules:

- Use each transform's owning module under `transforms/basic/`.

Adapter behavior:

- Signature: `(score: Score, params: Mapping[str, object]) -> Score`.
- Iterate `score.voices`.
- Use `flatten_voice_tones(voice)`.
- Validate and pass params to the existing raw tone-list transform.
- Return `Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=result)])]) ...])`.
- Preserve `"<each_voice>"` naming for now to avoid broad test churn.

Suggested tests:

```bash
uv run pytest tests/test_json_parser.py tests/test_transformation.py tests/test_transpose.py tests/test_scale.py tests/test_drift.py tests/test_repeat.py
```

### Batch 6: Score each-voice proportional/geological/complexity adapters

Extract named score adapters for:

- `golden_ratio`
- `weierstrass`
- `terraced_drift`
- `cellular_automata`
- `random_drop`

Also replace `feigenbaum_sequence` registry lambda with a named adapter that accepts `(score, params)` and calls `score_feigenbaum_sequence`.

Target modules:

- Use each transform's owning module.

Adapter behavior:

- Same score each-voice pattern as Batch 5.
- Preserve `"<each_voice>"` naming for each-voice outputs.
- Preserve `score_feigenbaum_sequence` behavior and its current generated motif naming unless a separate motif-name cleanup is explicitly requested.

Suggested tests:

```bash
uv run pytest tests/test_json_parser.py tests/test_transformation.py tests/test_proportion_feigenbaum.py tests/test_proportion_golden_ratio.py tests/test_geological_modulation.py
```

## Final Cleanup

Run these checks once all registry lambdas are removed:

```bash
rg -n "transform=lambda" transforms/registry.py
rg -n "\bcast\b" transforms/registry.py
uv run mypy .
uv run pytest tests
```

Expected final registry shape:

- `PHRASE_TRANSFORMS` entries use `PhraseTransformDefinition(..., transform=some_phrase_transform)`.
- `SCORE_TRANSFORMS` entries use `ScoreTransformDefinition(..., transform=some_score_transform)`.
- `transforms/registry.py` keeps only registry wiring, params specs, and adapter imports.
- `transforms/registry.py` should no longer import `Phrase`, `Motif`, `Voice`, `Score`, `flatten_voice_tones`, or `cast` unless a later design explicitly reintroduces them.

## Out Of Scope For This Cleanup

- Do not change public transform names.
- Do not change JSON composition format.
- Do not replace synthetic motif names like `"<transformed>"`, `"<each_voice>"`, or `"<feigenbaum>"` in this pass.
- Do not redesign `Motif.name`; that is a separate cleanup.


## Further cleanup after done

This is repeated in a lot of the adapter transforms:

```python
phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
```

Should this be extracted? look at the fucntions and see if there are common elements and patterns that shouled be extrascted to helper functions that can be shared.

- del params in one of the transforms is a smell. check on that (left a todo item)

- look at feigenbaum.py - that shape in the adapter is cleaner than other score transforms. Should we adopt that style to the other transforms?