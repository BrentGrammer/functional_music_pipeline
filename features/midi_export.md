# MIDI Export Feasibility

## Summary

Exporting this program's compositions to MIDI is feasible, but the best approach is not to convert the generated WAV file into MIDI.

The program should export MIDI directly from the internal `Score` model before audio rendering. The current pipeline already preserves enough structured musical information to support a MIDI writer:

- `Score` represents the full composition.
- `Voice` represents a monophonic sequence that can become a MIDI track.
- `Tone.frequency` can be converted to a MIDI note number.
- `Tone.duration` can be converted to MIDI ticks or beats.
- `Tone.amplitude` can be converted to MIDI velocity.
- `frequency == 0` can represent silence/rests.

## End Goal

The main user-facing goal is to export a transformed composition as a Standard MIDI File that can be imported into Cubase.

Once imported into Cubase, the MIDI should be usable with any VST instrument selected by the user. The exported MIDI does not need to contain audio or instrument sounds. It only needs to preserve the generated musical event data:

- note pitches
- note durations
- rests/silence
- voice separation as MIDI tracks
- note velocity derived from tone amplitude

The recommended output extension is `.mid`. Cubase and most DAW/tooling workflows recognize `.mid` as the standard extension for Standard MIDI Files. The CLI should use an explicit `--output-format midi` flag to choose MIDI output; the `.mid` filename extension should be documented as the recommended file naming convention, not used as the routing mechanism.

The intended workflow is:

```text
composition JSON
    -> transforms produce Score
    -> MIDI writer exports .mid
    -> Cubase imports .mid
    -> user assigns a VST instrument
    -> Cubase plays the generated composition through that VST
```

## Required Versus Optional MIDI Data

For the Cubase/VST workflow, the first MIDI exporter only needs note events with enough timing information to preserve the program's generated durations.

The following are not required for the first version:

- user-configurable BPM
- time signature
- MIDI channel assignment controls
- track names
- instrument metadata
- arbitrary overlapping note timing inside a single voice

Cubase can import a MIDI file without custom time-signature metadata, custom track names, or embedded instrument choices. The user can assign VST instruments, route tracks, and rename tracks inside Cubase.

MIDI channels are also not essential for the initial workflow if each `Voice` is exported as its own MIDI track. Cubase can handle the routing after import.

The exporter does still need an internal, deterministic conversion from the app's seconds-based `Tone.duration` values into MIDI ticks. This does not need to be exposed as a user-facing BPM setting. A fixed mapping such as `1 second = 960 ticks` is enough to preserve the generated note durations consistently.

Overlapping note timing inside a single `Voice` is not needed because the current domain model already treats each `Voice` as a monophonic sequence. Polyphonic playback comes from multiple voices playing as separate tracks.

## Architectural Fit

The current WAV output path renders a `Score` into audio through `audio_rendering/wav_writer.py`.

A MIDI export feature should sit beside that renderer instead of replacing it:

```text
score_model.Score
    -> audio_rendering/wav_writer.py
    -> midi_rendering/midi_writer.py
```

This keeps MIDI export aligned with the existing architecture:

- The parser and transforms continue producing `Score` objects.
- The WAV writer remains responsible only for audio output.
- A new MIDI writer becomes responsible only for MIDI file output.
- Transform behavior stays stateless and reusable across output formats.

## Frequency To MIDI Conversion

The main technical caveat is pitch representation.

The program currently stores pitch as raw frequency values, not note names or MIDI note numbers. Standard MIDI notes are integer semitone values, so frequencies need to be converted:

```text
midi_note = round(69 + 12 * log2(frequency / 440))
```

This works well for equal-tempered notes and most current composition examples.

## Microtonal MIDI Plan

Standard MIDI note events only represent integer semitone note numbers. A plain note event cannot directly represent a pitch between two semitones.

Microtonal MIDI export is still possible by combining normal note events with pitch bend:

```text
Tone.frequency
    -> nearest MIDI note
    -> cents difference from that note
    -> pitch bend event for the offset
    -> note-on/note-off events
```

This should be handled as a later export mode, after the basic MIDI writer is working.

The sensible staged plan is:

1. Implement normal MIDI export using rounded nearest MIDI notes.
2. Verify the exported `.mid` files import cleanly into Cubase and play through user-selected VST instruments.
3. Add a microtonal export mode using pitch bend for frequency offsets between semitones.
4. If independent simultaneous microtonal notes are needed later, investigate MPE-style or per-channel pitch-bend allocation.

The first microtonal implementation should probably start with per-voice pitch bend because the current `Voice` model is monophonic. Full polyphonic microtonality is more complex because pitch bend normally affects the entire MIDI channel.

## Microtonal Design Notes

The first microtonal version should treat each `Voice` as its own MIDI channel, or otherwise guarantee that only one pitch-bent note is active on a channel at a time. That makes pitch bend safe for the current monophonic voice model.

To make the bend values predictable, the exporter should explicitly set the pitch bend range on each used channel before writing notes. Otherwise, the amount of tuning applied by the target synth or Cubase instrument can vary.

The default pitch bend range for microtonal export should be `+- 1 semitone`. That gives enough room for the common case where a frequency is rounded to the nearest MIDI note and then nudged slightly above or below it for microtonal accuracy.

Do not rely on the target VST's default bend range. The MIDI export should set the bend sensitivity explicitly so the tuning is reproducible across instruments.

The practical conversion path is:

1. Convert the tone frequency to the nearest MIDI note number.
2. Compute the cents difference between the tone frequency and that note.
3. Convert that cents offset into a pitch bend value within the configured bend range.
4. Emit the bend value before the note-on event.
5. Reset the bend back to center after the note, if needed.

This works well for:

- single-note microtonal melody lines
- voice-by-voice microtonal export

It does not fully solve:

- independent microtonal intervals in chords on the same MIDI channel
- simultaneous microtonal notes that require different bends at the same time

If we need that later, the next step is MPE-style per-note channel allocation or a more advanced MIDI tuning strategy.

Compatibility note: pitch-bend microtonal export will only sound correct if the target VST or synth supports pitch bend in a predictable way. Some instruments support it well, some only within a limited range, and some may ignore it or use a fixed bend behavior that is not useful for microtonal playback.

## Caveats

- Frequencies that do not land exactly on equal-tempered semitones will be rounded to the nearest MIDI note.
- Algorithmic transforms that create microtonal frequencies will lose that microtonal detail in a basic MIDI export.
- Microtonal MIDI export should be implemented after the first rounded-note MIDI exporter is working.
- Pitch bend range must be set explicitly if we want predictable tuning across instruments.
- Full independent polyphonic microtonality may require MPE-style or per-channel pitch-bend allocation.
- MIDI duration needs a deterministic seconds-to-ticks conversion, but this can be fixed internally rather than user-configurable.
- Amplitude can map to MIDI velocity, but the mapping should clamp values into the valid MIDI range.

## First Iteration Proposal

Implement a basic Standard MIDI File exporter with these behaviors:

- Add a MIDI file-writing dependency. Prefer `mido` unless implementation work reveals a better fit.
- Add `midi_rendering/midi_writer.py`.
- Export each `Voice` as a separate MIDI track.
- Convert nonzero `Tone.frequency` values to nearest MIDI notes.
- Treat `frequency == 0` or `amplitude == 0` as rests.
- Convert `Tone.duration` seconds into MIDI ticks using a fixed internal mapping.
- Convert `Tone.amplitude` into MIDI velocity.
- Add a CLI option that lets users choose MIDI output with `--output-format midi`.
- Do not implement pitch bend or microtonal export in the first iteration.

This first version should be useful for importing transformed compositions into Cubase while keeping the implementation small and compatible with the current score model.

## Concrete Implementation Plan

1. Add the MIDI dependency.
   - 1.1. Add `mido` to `requirements.txt`.

2. Create the MIDI rendering package.
   - 2.1. Add `midi_rendering/__init__.py`.
   - 2.2. Add `midi_rendering/midi_writer.py`.

3. Implement focused conversion helpers.
   - 3.1. Add `frequency_to_midi_note(frequency: float) -> int`.
   - 3.2. Add `amplitude_to_velocity(amplitude: float) -> int`.
   - 3.3. Add `duration_to_ticks(duration: float) -> int`.

4. Implement score export.
   - 4.1. Add `save_score_to_midi(score: Score, filename: str) -> None`.
   - 4.2. Create one MIDI track per `Voice`.
   - 4.3. Write sequential note events for each `Tone` in that voice.
   - 4.4. Accumulate rest duration as delta time before the next note.
   - 4.5. Clamp MIDI notes and velocities to valid MIDI ranges.

5. Wire MIDI export into the CLI.
   - 5.1. Keep the existing WAV behavior unchanged.
   - 5.2. If `--output-format midi` is selected, call the MIDI writer.
   - 5.3. Otherwise, keep writing WAV through `save_score_to_wav`.

6. Add tests.
   - 6.1. Test frequency-to-note conversion for known pitches such as A4 = 440 Hz -> 69.
   - 6.2. Test non-exact frequencies round to the nearest MIDI note.
   - 6.3. Test amplitude-to-velocity clamps into the valid MIDI range.
   - 6.4. Test duration-to-ticks uses the fixed internal mapping.
   - 6.5. Test rests delay the next note instead of producing a note event.
   - 6.6. Test each `Voice` becomes a separate MIDI track.
   - 6.7. Test CLI routing selects MIDI export for `--output-format midi` and WAV export otherwise.

7. Verify.
   - 7.1. Manually generate a small `.mid` file from an existing composition and import it into Cubase when available.

8. Update the README.md for the program to indicate this feature is possible for the user to use. They can export the composition to a midi format and import it in their DAW (such as Cubase).
