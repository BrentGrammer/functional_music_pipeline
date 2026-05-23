# Refactor Frost Effect

## Background

The current `frost_effect` transform is score-scoped and works by selecting the earliest audible voice or cluster of voices, then expanding only the first audible tone from each selected voice. In a single melodic voice, this means the transform effectively grows from one note instead of responding to the full transformed phrase or motif.

That behavior is not the desired musical model for melodic material. If a phrase or motif contains multiple audible notes, the expected result is that each note acts as its own local frost seed. The frost effect should then create upper and lower edge expansions for each note over the requested number of iterations, with all generated results playing polyphonically.

## Desired Behavior

- Keep `frost_effect` as a score-level transform for now.
- Do not add phrase-level JSON support in this refactor.
- Preserve the existing public transform name and params:
  - `name`: `frost_effect`
  - `params.iterations`: positive integer
- Add an optional public transform param:
  - `params.sustain_notes`: boolean
  - defaults to `false` when omitted
  - users must explicitly set it to `true` to enable duration extension
- Change the score-level behavior so every audible tone in the input score becomes a local frost seed.
- For each local seed tone, preserve the current single-note behavior:
  - replay the source tone in the frost generation
  - add one lower edge and one upper edge
  - repeat this process for each requested iteration
  - keep stochastic outward movement within the existing cent bounds
- Preserve the existing stochastic rhythmic behavior:
  - randomized stagger timing stays intact
  - randomized edge order stays intact
  - `sustain_notes` must not change generated note start times
- When `sustain_notes` is `true`, extend generated frost note durations after the normal stochastic scheduling is complete.
  - For each local frost generation, find the latest audible end time among that generation's generated notes.
  - Extend each generated frost note in that local generation so it ends at the same latest end time.
  - Do not alter the original source score voices.
- When `sustain_notes` is omitted or `false`, generated frost notes keep their normal short staggered durations.
- Schedule each local frost expansion relative to the source note's own start/end time, not only after the whole score.
- Preserve the original score voices and append generated frost voices so the frost output plays polyphonically against the source material and other local frost events.

## Current Design Constraint

Phrase transforms currently return a single `Phrase`. Frost is polyphonic and needs to add auxiliary `Voice` objects. Because of that, true phrase-level frost requires a broader transform contract change and should be deferred.

The useful near-term refactor is to isolate the single-note frost expansion behavior so score-level frost can apply it to every audible tone. That same internal behavior can later be reused if phrase-level transforms gain a way to contribute auxiliary voices.

## Proposed Implementation

1. Add an internal seed event representation that carries:
   - source `Tone`
   - absolute source start time
   - source end time

2. Add a helper that walks all score voices and collects every audible tone:
   - `frequency > 0`
   - `amplitude > 0`
   - `duration > 0`

3. Extract the current single-note frost behavior into a local expansion helper.
   - The helper should accept one seed event and `iterations`.
   - The helper should accept `sustain_notes`, defaulting to `False` at the public param layer.
   - It should generate voices for each local generation.
   - Each generation should replay the previous local event and add one lower and one upper edge.
   - It should apply duration extension only after each generation's stochastic notes have been scheduled.

4. Update `frost_effect(score, iterations, sustain_notes=False)` to:
   - validate `iterations`
   - parse and validate optional `sustain_notes`
   - copy/preserve original score voices
   - collect all audible seed events
   - generate local frost voices for every seed event
   - return the original voices plus generated voices

5. Keep phrase-level support out of scope.

## Testing Plan

- Add tests for collecting audible seed events across:
  - multiple tones in one voice
  - multiple phrases in one voice
  - multiple voices
  - leading silence
  - rests and zero-amplitude tones
- Add tests proving a multi-note line expands every note, not just the first note.
- Add tests that each local seed preserves the current single-note frost behavior:
  - replayed source tone exists
  - lower and upper edges are added
  - edge movement remains within existing cent bounds
  - later generations expand from the previous local generation
- Add tests for `sustain_notes`:
  - omitted `sustain_notes` defaults to `false`
  - non-boolean `sustain_notes` is rejected
  - `sustain_notes: false` preserves current generated note durations
  - `sustain_notes: true` keeps stochastic staggered starts but extends generated notes to the latest audible end time in each local generation
- Rewrite existing tests that assume one global frost field expansion from the earliest voice/cluster.
- Run targeted frost tests before broader suite verification.

## Demo Impact

After this refactor, the existing frost demos should be rerendered. In particular, `emergent_pipeline_frost_bloom_demo.json` should sound more coherent because the frost bloom will respond to every note in the transformed output instead of spreading from only the first audible note.
