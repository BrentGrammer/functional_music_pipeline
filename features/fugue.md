# Feature: Fugue Operations

## Status

Planned, but intentionally small. Most conventional fugue techniques are already expressible with the current composition JSON, voice structure, and transform pipeline.

## Goal

Keep fugue support aligned with the application's core style: user-directed composition from small motifs and transform pipelines.

This feature should not add transforms for behavior already available through the current system. New helpers should only be added when the existing JSON becomes awkward for a common fugue task.

## First-Class Concepts

- **Subject**: The primary thematic motif used by later entries.
- **Answer**: A subject entry in another voice, optionally transformed by an explicit existing transform pipeline.
- **Countersubject**: A recurring line that accompanies subject or answer entries.
- **Pedal Point**: A sustained or repeated anchor tone in one voice while other voices continue contrapuntal material.
- **Golden-Ratio Stretto**: A stretto effect whose voice-entry delays are spaced by golden-ratio-related values.

## Already Supported

- Subject and answer entries can be written as named motifs in separate voices.
- Answers can be transformed by applying existing phrase transforms in JSON.
- Stretto can be written manually with multiple voices and `delay`.
- Countersubjects can be written as their own motifs and placed in another voice.
- Episodes can be composed from motifs, phrase concatenation, and existing transforms.

## Possible New Helper

### Pedal Point

A pedal point helper may be useful because manually authoring a sustained or repeated anchor tone for a target duration is repetitive. The helper should add a sustained or repeated tone voice while preserving the rest of the score.

Suggested parameters:

- `frequency`
- `duration`
- optional `amplitude`
- optional `mode`: `sustain` or `repeat`
- optional `pulse_duration` for repeated pedal tones

### Golden-Ratio Stretto

A golden-ratio stretto helper may be useful because the user can already make stretto manually with multiple voices and `delay`, but calculating and maintaining golden-ratio-related entry offsets by hand is awkward.

The helper should remain user-directed: the user supplies the subject material or source voice, target voices, and a base delay or total overlap window. The helper only calculates golden-ratio-spaced entry offsets and places the entries.

Suggested parameters:

- `source_voice` or source motif/phrase reference
- `target_voices`
- `base_delay` or `overlap_window`
- optional transforms per entry
- optional spacing direction, such as `contracting` or `expanding`

## Episode Support

Episodes should not be implemented as a first-class fugue operation. They are compositional passages that the user can already build from motifs and transform pipelines.

## Proposed Implementation Order

1. Add pedal point placement as a small score-level helper.
2. Add focused composition JSON demos showing how to write fugal techniques using the current composition JSON API.
3. Add golden-ratio stretto as a small helper if the manual demo shows the offset math is too awkward to maintain by hand.

## Decisions

- Fugue information should be specified by the user in the composition JSON. The system should not infer fugue structure implicitly from existing motifs.
- Fugue helpers should wrap existing building blocks where useful rather than introduce a separate scheduling model.
- Voice-specific transforms should usually be written directly inside the target voice's phrases. A post-score single-voice transform is not required for fugue support unless repeated JSON becomes a concrete problem.
- Score-aware fugue operations should start in `transforms/fugue.py` to match the existing parser and transform registration pattern. Move to a separate package only if the feature grows beyond a single cohesive module.
- The current fugue feature scope is limited to the pedal point helper, fugal composition demos, and a possible golden-ratio stretto helper. Other helpers should be deferred until real composition examples show a concrete need.
