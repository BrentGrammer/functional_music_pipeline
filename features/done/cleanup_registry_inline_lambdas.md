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
            motifs=[Motif(name="", tones=reverse_tones([... for ...]))]
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

## Reference Implementations

Every adapter function follows one of these exact patterns. The implementing model should use these as templates — copy the structure, swap in the raw function name and params.

### Phrase adapter — no params

```python
def invert_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    del params
    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    result = invert_tones(phrase_tones)
    return Phrase(motifs=[Motif(name="", tones=result)])
```

### Phrase adapter — with params (required float + required string)

```python
def pad_silence_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")
    position = params["position"]
    if not isinstance(position, str):
        raise ValueError("Param 'position' must be a string.")
    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    result = pad_silence_tones(phrase_tones, seconds=float(seconds), position=position)
    return Phrase(motifs=[Motif(name="", tones=result)])
```

### Phrase adapter — with optional dimension param

```python
def feigenbaum_sequence_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension", ToneDimension.DURATION)
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Param 'dimension' must be a string or ToneDimension.")
    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    result = feigenbaum_sequence(phrase_tones, dimension=dimension)
    return Phrase(motifs=[Motif(name="", tones=result)])
```

### Phrase adapter — phrase-relative (HIGH complexity)

```python
def phrase_feigenbaum_shrink_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension", ToneDimension.DURATION)
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Param 'dimension' must be a string or ToneDimension.")

    current_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]

    if context.phrase_index > 0:
        reference_phrases = context.score.voices[context.voice_index].phrases[:context.phrase_index]
    elif context.voice_index > 0:
        reference_phrases = context.score.voices[context.voice_index - 1].phrases
    else:
        reference_phrases = []

    reference_tones = [
        tone
        for phrase in reference_phrases
        for motif in phrase.motifs
        for tone in motif.tones
    ]

    result = phrase_feigenbaum_shrink(current_tones, reference_tones, dimension=dimension)
    return Phrase(motifs=[Motif(name="", tones=result)])
```

### Score adapter — each-voice with params

```python
def scale_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    dimension = params["dimension"]
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Param 'dimension' must be a string or ToneDimension.")
    factor = params["factor"]
    if isinstance(factor, bool) or not isinstance(factor, (int, float)):
        raise ValueError("Param 'factor' must be a float.")

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        result = scale_transform(voice_tones, dimension=dimension, factor=float(factor))
        new_voices.append(
            Voice(phrases=[Phrase(motifs=[Motif(name="", tones=result)])])
        )
    return Score(voices=new_voices)
```

### Score adapter — delegates to another function

```python
def frost_effect_score_adapter(score: Score, params: Mapping[str, object]) -> Score:
    iterations = params.get("iterations", 1)
    if isinstance(iterations, bool) or not isinstance(iterations, int):
        raise ValueError("Param 'iterations' must be an integer.")
    return frost_effect(score, iterations=iterations)
```

---

## Implementation Plan

Each step changes one well-defined thing, leaves the codebase in a working state, and has a clear "done" signal.

Tags:
- **(low)** — mechanical extraction using a reference template. Copy, adapt, wire.
- **(high)** — involves nested logic or coordinated edits. See reference implementation for exact code.

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

### Step 3a (low): Extract `invert` phrase adapter

Add `invert_phrase_transform` to `transforms/basic/inversion.py`. Follow the **Phrase adapter — no params** reference template. The raw function is `invert_tones`.
Import `Mapping` from `collections.abc`, `PhraseTransformContext` from `transforms.base`, `Motif` from `score_model.motif`, `Phrase` from `score_model.phrase`.

Update the phrase registry entry and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 3b (low): Extract `feigenbaum_sequence` and `erosion` phrase adapters

Add `feigenbaum_sequence_phrase_transform` to `transforms/proportion/feigenbaum.py`. Follow the **Phrase adapter — with optional dimension param** reference template. The raw function is `feigenbaum_sequence`.

Add `erosion_phrase_transform` to `transforms/geological/erosion.py`. Same reference template. The raw function is `erosion_transform`.

Both use `params.get("dimension", ToneDimension.DURATION)` and narrow with `isinstance(value, (str, ToneDimension))`.

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py tests/test_proportion_feigenbaum.py` passes. `uv run mypy .` passes.

---

### Step 4 (low): Extract single-required-param phrase adapters

Three transforms, one param each. Follow the **Phrase adapter — with params** reference template, adapted for single-param access.

| Registry key | Param | Narrowing | Module |
|---|---|---|---|
| `transpose` | `semitones` | `isinstance(v, bool) or not isinstance(v, (int, float))` | `transforms/basic/transpose.py` |
| `delay` | `seconds` | same as above | `transforms/basic/delay.py` |
| `repeat` | `count` | `isinstance(v, bool) or not isinstance(v, int)` | `transforms/basic/repeat.py` |

Naming: `{key}_phrase_transform`.

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 5a (low): Extract `scale`, `drift`, `pad_silence` phrase adapters

Follow the **Phrase adapter — with params** reference template. Two required params each.

| Registry key | Params | Module |
|---|---|---|
| `scale` | `dimension` (`ToneDimension | str`), `factor` (`float`) | `transforms/basic/scale.py` |
| `drift` | `dimension` (`ToneDimension | str`), `rate` (`float`) | `transforms/basic/drift.py` |
| `pad_silence` | `seconds` (`float`), `position` (`str`) | `transforms/basic/pad_silence.py` |

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 5b (low): Extract `golden_ratio`, `weierstrass`, `terraced_drift` phrase adapters

| Registry key | Params | Module |
|---|---|---|
| `golden_ratio` | `dimension` (optional, `ToneDimension | str`, default `ToneDimension.DURATION`) | `transforms/proportion/golden_ratio.py` |
| `weierstrass` | `dimension` (`ToneDimension | str`), `intensity` (`str`) | `transforms/complexity/weierstrass.py` |
| `terraced_drift` | `dimension` (`ToneDimension | str`), `max_step_change_pct` (`int`) | `transforms/geological/terraced_drift.py` |

`golden_ratio` uses `params.get(...)` narrowing (see optional-dimension template). The other two use `params[...]` (required).

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 5c (low): Extract `accelerando` and `ritardando` phrase adapters

These have two optional `str | float` params with string defaults. Narrow each with `isinstance(value, (str, float))`.

| Registry key | Params (both `str | float`) | Defaults | Module |
|---|---|---|---|---|
| `accelerando` | `strength`, `jaggedness` | `"medium"`, `"none"` | `transforms/tempo/accelerando.py` |
| `ritardando` | `strength`, `jaggedness` | `"medium"`, `"none"` | `transforms/tempo/ritardando.py` |

```python
strength = params.get("strength", "medium")
if not isinstance(strength, (str, float)):
    raise ValueError("Param 'strength' must be a string or float.")
# same for jaggedness
```

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 6 (low): Extract multi-param phrase adapters

| Registry key | Params | Module |
|---|---|---|
| `cellular_automata` | `dimension` (`ToneDimension | str`), `rule` (`int`), `generations` (`int`), `max_deviation` (`float`) | `transforms/complexity/cellular_automata.py` |
| `random_drop` | `dimension` (`ToneDimension | str`), `max_drop_pct` (`int`), `drop_frequency_pct` (`int`) | `transforms/complexity/random_drop.py` |

Same pattern as two-param adapters, just more params. Follow the reference template.

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 7 (high): Extract phrase-relative adapters

These transforms compute reference tones from neighboring phrases. Use the **Phrase adapter — phrase-relative** reference template exactly. Copy it, change the raw function call, and update the module.

| Registry key | Raw function | Module |
|---|---|---|
| `phrase_feigenbaum_shrink` | `phrase_feigenbaum_shrink` | `transforms/proportion/feigenbaum.py` |
| `phrase_feigenbaum_grow` | `phrase_feigenbaum_grow` | `transforms/proportion/feigenbaum.py` |
| `phrase_golden_ratio_shrink` | `phrase_golden_ratio_shrink` | `transforms/proportion/golden_ratio.py` |
| `phrase_golden_ratio_grow` | `phrase_golden_ratio_grow` | `transforms/proportion/golden_ratio.py` |

All four use the same reference-tone derivation logic. The only difference is which raw function is called.

Do not extract the reference-tone derivation into a shared helper — inline it in each adapter per the standing "no new helpers unless 3+ call sites" rule (these are 4 call sites spread across 2 modules, which is borderline; default to inlining).

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py tests/test_proportion_feigenbaum.py tests/test_proportion_golden_ratio.py` passes. `uv run mypy .` passes.

---

### Step 8a (low): Extract basic module score each-voice adapters

Follow the **Score adapter — each-voice with params** reference template.

| Registry key | Module |
|---|---|
| `invert` | `transforms/basic/inversion.py` |
| `transpose` | `transforms/basic/transpose.py` |
| `scale` | `transforms/basic/scale.py` |
| `delay` | `transforms/basic/delay.py` |
| `repeat` | `transforms/basic/repeat.py` |
| `drift` | `transforms/basic/drift.py` |

`invert` has no params — simplify the template by removing param narrowing (`del params` instead).
The other five use the full template with their respective params.

Naming: `{key}_score_transform`.

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 8b (low): Extract complexity module score each-voice adapters

| Registry key | Module |
|---|---|
| `weierstrass` | `transforms/complexity/weierstrass.py` |
| `cellular_automata` | `transforms/complexity/cellular_automata.py` |
| `random_drop` | `transforms/complexity/random_drop.py` |

Same reference template. `cellular_automata` and `random_drop` have more params — follow the multi-param phrase pattern applied to the score template.

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 8c (low): Extract geological module score each-voice adapters

| Registry key | Module |
|---|---|
| `golden_ratio` | `transforms/proportion/golden_ratio.py` |
| `terraced_drift` | `transforms/geological/terraced_drift.py` |

`golden_ratio` uses optional `dimension` (default `ToneDimension.DURATION`). `terraced_drift` has required params.

Update the registry entries and imports.

Done signal: `uv run pytest tests/test_json_parser.py` passes. `uv run mypy .` passes.

---

### Step 9 (low): Create adapters for `feigenbaum_sequence` and `frost_effect` score transforms

These two score entries currently unpack params with `**params` directly into the raw function. Replace with proper adapter functions.

| Registry key | Adapter name | Module | Template |
|---|---|---|---|
| `feigenbaum_sequence` | `score_feigenbaum_sequence_adapter` | `transforms/proportion/feigenbaum.py` | Optional-dimension pattern (default `ToneDimension.DURATION`) |
| `frost_effect` | `frost_effect_score_adapter` | `transforms/geological/frost_effect.py` | **Score adapter — delegates to another function** reference template |

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

### Step 11 (low): Replace angle-bracket synthetic Motif names with empty string

The codebase uses angle-bracket strings (`"<transformed>"`, `"<each_voice>"`, `"<parsed>"`, `"<frost_copy>"`, `"<frost>"`, `"<feigenbaum>"`, `"<pedal>"`) as `Motif.name` values for motifs that are generated by transforms rather than defined by the user. These names carry no information — they exist solely because `Motif` requires a `name` field.

Replace all synthetic motif names with `""` (empty string). The empty string is honest: it means "this motif has no user-assigned name."

**Mechanical replacement — no design judgment needed:**

| Current name | Replace with |
|---|---|
| `"<transformed>"` | `""` |
| `"<each_voice>"` | `""` |
| `"<parsed>"` | `""` |
| `"<frost_copy>"` | `""` |
| `"<frost>"` | `""` |
| `"<feigenbaum>"` | `""` |
| `"<pedal>"` | `""` |

Step-by-step:

1. Search: `rg -l 'name="<' transforms/ composition/ --type py` to find affected files.
2. In each file, replace every `name="<...>"` with `name=""`.
3. Search: `rg '"<(transformed|each_voice|parsed|frost_copy|frost|feigenbaum|pedal)>"' tests/ --type py` to find test assertions.
4. Replace each test assertion string `"<...>"` with `""`.
5. Run `uv run pytest tests` — full suite must pass.
6. Run `uv run mypy .` — must pass.
7. Run `rg 'name="<' transforms/ composition/ tests/ --type py` — should return zero results.

Done signal: zero angle-bracket motif names in production code or tests. Full suite green. `mypy .` green.

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

## Open Item: Synthetic Motif Names

### The Problem

Transforms produce `Motif` objects to hold their output tones. These motifs have no meaningful name — they are not authored in JSON and are never referenced by name. But `Motif.name` is currently typed as `str` (required), which forces the code to invent fake values.

The codebase currently uses angle-bracket strings: `"<transformed>"`, `"<each_voice>"`, `"<parsed>"`, `"<frost_copy>"`, `"<frost>"`, `"<feigenbaum>"`, `"<pedal>"`. These exist only to satisfy the type checker. No code branches on them. They are noise.

### What `Motif.name` Is Actually Used For

In production code, `Motif.name` is read in exactly two places:

1. **`build_score`** in `composition/transformer.py` — copies `plan_motif.name` (a real user-authored name) onto the new motif.
2. **`find_motif_by_name`** in `transforms/counterpoint/fugue.py` — used by `stretto` to look up a target motif by name in the score hierarchy.

That's it. Both are for user-authored motifs where the name actually matters.

### Public API Reality

In the JSON composition format, every motif is authored with a name in the top-level `motifs` block, and phrases reference those names:

```json
"motifs": { "seed": ["440:0.5"] },
"phrases": [{ "motifs": ["seed"] }]
```

Phrases cannot contain raw tone strings. They always reference named motifs. So at the authoring level, motifs always have names.

But transform-generated motifs are never authored, never appear in JSON, and are never referenced by name. They are internal containers for tone sequences.

### Options Considered

**Option A: Replace angle brackets with empty string `""`**
- Replaces one fake value with another. `""` is still a magic value pretending to mean "no name."
- Smell: the type system says name is required, but the value says it isn't.

**Option B: Make `Motif.name` optional — `str | None = None`**
- Authoring: `build_score` always passes `name=plan_motif.name` (a real string).
- Transforms: adapters create `Motif(tones=result)` without a name.
- `find_motif_by_name`: `None == "some_name"` is `False`, so synthetic motifs are naturally skipped.
- Honest at the type level: a motif may or may not have a name.

**Option C: Drop `name` from `Motif` entirely**
- Keep the name→Motif mapping in `ScorePlan.motifs: dict[str, Motif]`.
- `stretto` would need an alternative lookup mechanism (e.g., a name index on `Score` or traversal of `ScorePlan`).
- Cleaner separation but larger change.

**Option D: Separate authored and synthetic types**
- Two classes (e.g., `NamedMotif` and `AnonymousMotif`).
- Adds complexity. `Phrase.motifs` would need a union type. Minimal benefit.

### Current Direction

Step 11 currently proposes replacing angle brackets with `""`. This is intentionally mechanical and non-disruptive so the registry cleanup can proceed independently.

The real fix — making `name` optional on `Motif` — is recorded here as a follow-up item. It is small (one line change to the constructor signature, plus test assertion updates) and eliminates the fake-value problem entirely without adding new types. It should be addressed after the registry cleanup lands.