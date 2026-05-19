# Feature: Clean Up Registry Inline Lambdas

## Context

The transform registry (`transforms/registry.py`) contains two dictionaries that are bloated with inline lambdas. Each lambda repeats the same adaptation work: extract tones, narrow parameters with `cast`, call a raw transform function, and wrap the result. The registry is doing dispatch, parameter recovery, type narrowing, and adaptation all in one place.

This makes the registry hard to read, hard to type-check, and impossible to maintain without adding more `cast` calls or little helpers. The earlier observation note (`registry_typing_smell_observation.md`) identified the root cause: a single generic layer trying to represent many distinct call signatures through `Mapping[str, object]`.

## Goal

The registry becomes a clean name-to-definition mapping. Each transform module owns its own adapter function. The registry imports and references those functions directly — no inline lambdas, no `cast`, no parameter extraction logic.

Before:

```python
PHRASE_TRANSFORMS = {
    "reverse": PhraseTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[Motif(name="<transformed>", tones=reverse_tones([... for ...]))]
        ),
    ),
    ...
}
```

After:

```python
PHRASE_TRANSFORMS = {
    "reverse": PhraseTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform=reverse_phrase_transform,
    ),
    ...
}
```

The adapter functions (`reverse_phrase_transform`, etc.) live in the same modules as their raw transform functions. They own the adaptation logic: reading tones from context, narrowing parameters with `isinstance`, calling the raw function, and wrapping the result. The registry just wires them together.

## Design Constraints

- No `cast`. No `Any`.
- Parameter narrowing uses `isinstance` checks inside adapter functions.
- Adapter functions live in the transform's own module (e.g., `transforms/basic/reversal.py`).
- Each adapter follows the definition's typed signature: `(PhraseTransformContext, Mapping[str, object]) -> Phrase` or `(Score, Mapping[str, object]) -> Score`.
- The registry does not own adaptation logic.
- Standing rule from the parent refactor: no new helper functions unless the same logic is needed in 3+ call sites.

## Implementation Plan

Each step changes one well-defined thing, leaves the codebase in a working state, and has a clear "done" signal.

All steps are tagged **(low)** — they are mechanical extractions of existing logic into named functions with `isinstance`-based parameter narrowing.

---

### Step 1 (low): Fix `SCORE_TRANSFORMS` type annotation

Change line 436 from `SCORE_TRANSFORMS: dict[str, object] = {` to `SCORE_TRANSFORMS: dict[str, ScoreTransformDefinition] = {`.

Done signal: `uv run mypy .` passes.

---

### Step 2 (low): Wire existing adapter functions into the registry

Two adapter functions already exist but the registry uses inline lambdas instead:

- `reverse_phrase_transform` in `transforms/basic/reversal.py`
- `reverse_score_transform` in `transforms/basic/reversal.py`

Update the phrase registry `"reverse"` entry to use `transform=reverse_phrase_transform`.  
Update the score registry `"reverse"` entry to use `transform=reverse_score_transform`.

Add the import of these two functions to the registry.

Done signal: `uv run pytest tests/test_json_parser.py tests/test_transformation.py` passes. `uv run mypy .` passes.

---

### Step 3 (low): Extract no-param own-phrase adapters

These phrase transforms take no parameters. Each gets one named adapter function in its own module. The adapter: reads tones from `context.phrase`, calls the raw function, wraps in `Phrase(motifs=[Motif(name="<transformed>", tones=result)])`.

| Registry key | Raw function | Module to add adapter |
|---|---|---|
| `invert` | `invert_tones` | `transforms/basic/inversion.py` |
| `feigenbaum_sequence` | `feigenbaum_sequence` | `transforms/proportion/feigenbaum.py` |
| `erosion` | `erosion_transform` | `transforms/geological/erosion.py` |

For `feigenbaum_sequence` and `erosion`, the raw function has an optional `dimension` parameter. The adapter reads it from `params` with an `isinstance` check and a default of `ToneDimension.DURATION`.

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py tests/test_proportion_feigenbaum.py` passes. `uv run mypy .` passes.

---

### Step 4 (low): Extract single-required-param own-phrase adapters

These phrase transforms take exactly one required parameter. Each gets a named adapter that reads the param from `params`, narrows with `isinstance`, and passes it to the raw function.

| Registry key | Param | Type | Module |
|---|---|---|---|
| `transpose` | `semitones` | `float` | `transforms/basic/transpose.py` |
| `delay` | `seconds` | `float` | `transforms/basic/delay.py` |
| `repeat` | `count` | `int` | `transforms/basic/repeat.py` |

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 5 (low): Extract two-param own-phrase adapters

| Registry key | Params | Types | Module |
|---|---|---|---|
| `scale` | `dimension`, `factor` | `ToneDimension \| str`, `float` | `transforms/basic/scale.py` |
| `drift` | `dimension`, `rate` | `ToneDimension \| str`, `float` | `transforms/basic/drift.py` |
| `pad_silence` | `seconds`, `position` | `float`, `str` | `transforms/basic/pad_silence.py` |
| `weierstrass` | `dimension`, `intensity` | `ToneDimension \| str`, `str` | `transforms/complexity/weierstrass.py` |
| `terraced_drift` | `dimension`, `max_step_change_pct` | `ToneDimension \| str`, `int` | `transforms/geological/terraced_drift.py` |
| `golden_ratio` | `dimension` (optional) | `ToneDimension \| str` | `transforms/proportion/golden_ratio.py` |

`golden_ratio` has only one optional param — group it here since its raw function takes `(tones, dimension)`.

For `accelerando` and `ritardando` (two optional params with defaults: `strength` and `jaggedness`, both `str | float`), add adapters in `transforms/tempo/accelerando.py` and `transforms/tempo/ritardando.py`.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 6 (low): Extract multi-param own-phrase adapters

| Registry key | Params | Types | Module |
|---|---|---|---|
| `cellular_automata` | `dimension`, `rule`, `generations`, `max_deviation` | `ToneDimension \| str`, `int`, `int`, `float` | `transforms/complexity/cellular_automata.py` |
| `random_drop` | `dimension`, `max_drop_pct`, `drop_frequency_pct` | `ToneDimension \| str`, `int`, `int` | `transforms/complexity/random_drop.py` |

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 7 (low): Extract phrase-relative adapters

These transforms access neighboring phrases through `context.score` / `context.voice_index` / `context.phrase_index`. The adaptation logic (computing reference tones) is currently duplicated across four inline lambdas. Extract it once into each module.

| Registry key | Raw function | Module |
|---|---|---|
| `phrase_feigenbaum_shrink` | `phrase_feigenbaum_shrink` | `transforms/proportion/feigenbaum.py` |
| `phrase_feigenbaum_grow` | `phrase_feigenbaum_grow` | `transforms/proportion/feigenbaum.py` |
| `phrase_golden_ratio_shrink` | `phrase_golden_ratio_shrink` | `transforms/proportion/golden_ratio.py` |
| `phrase_golden_ratio_grow` | `phrase_golden_ratio_grow` | `transforms/proportion/golden_ratio.py` |

Each adapter:
1. Reads current phrase tones from `context.phrase`.
2. Derives reference tones from earlier phrases in the same voice, or the previous voice, or empty list.
3. Reads optional `dimension` from `params` with `isinstance` check and default.
4. Calls the raw function.
5. Wraps in `Phrase(motifs=[Motif(name="<transformed>", tones=result)])`.

Done signal: `uv run pytest tests/test_json_parser.py tests/test_proportion_feigenbaum.py tests/test_proportion_golden_ratio.py` passes. `uv run mypy .` passes.

---

### Step 8 (low): Extract score each-voice adapters

Every each-voice score transform follows the same pattern: iterate `score.voices`, read `flatten_voice_tones(voice)`, call raw function with narrowed params, wrap each voice. Extract each into a named function in the raw transform's module.

These are the score-registry entries that currently use inline lambdas iterating voices:

| Registry key | Module |
|---|---|
| `golden_ratio` | `transforms/proportion/golden_ratio.py` |
| `invert` | `transforms/basic/inversion.py` |
| `transpose` | `transforms/basic/transpose.py` |
| `scale` | `transforms/basic/scale.py` |
| `delay` | `transforms/basic/delay.py` |
| `repeat` | `transforms/basic/repeat.py` |
| `drift` | `transforms/basic/drift.py` |
| `weierstrass` | `transforms/complexity/weierstrass.py` |
| `terraced_drift` | `transforms/geological/terraced_drift.py` |
| `cellular_automata` | `transforms/complexity/cellular_automata.py` |
| `random_drop` | `transforms/complexity/random_drop.py` |

Each adapter follows `(Score, Mapping[str, object]) -> Score`, narrows params with `isinstance`, iterates voices, and returns a new `Score`. `reverse_score_transform` in `reversal.py` is the reference implementation.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 9 (low): Create adapters for `feigenbaum_sequence` and `frost_effect` score transforms

These two score entries currently unpack params with `**params` directly into the raw function. Replace with proper adapter functions that narrow params with `isinstance`.

- `score_feigenbaum_sequence_adapter` → `transforms/proportion/feigenbaum.py` (reads optional `dimension` param)
- `frost_effect_score_adapter` → `transforms/geological/frost_effect.py` (reads optional `iterations` param)

Update registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py tests/test_frost_effect_demo.py` passes. `uv run mypy .` passes.

---

### Step 10 (low): Verify and clean up

- Run `rg "lambda.*context.*params" transforms/registry.py` — should return zero results.
- Run `rg "\bcast\b" transforms/registry.py` — should return zero results.
- Run `uv run mypy .` — must pass.
- Run `uv run pytest tests` — full suite must pass.

Done signal: all of the above clean.

---

## Estimated Final Shape

```python
# transforms/registry.py

PHRASE_TRANSFORMS: dict[str, PhraseTransformDefinition] = {
    "reverse": PhraseTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform=reverse_phrase_transform,
    ),
    "invert": PhraseTransformDefinition(
        name="invert",
        params_spec=INVERT_PARAMS_SPEC,
        transform=invert_phrase_transform,
    ),
    ...
}

SCORE_TRANSFORMS: dict[str, ScoreTransformDefinition] = {
    "reverse": ScoreTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform=reverse_score_transform,
    ),
    "add_pedal_tone": ScoreTransformDefinition(
        name="add_pedal_tone",
        params_spec=ADD_PEDAL_TONE_PARAMS_SPEC,
        transform=add_pedal_tone_score_transform,
    ),
    ...
}
```

Each transform module owns its adapter function. The registry is a clean wiring layer — no lambdas, no `cast`, no inline logic.
