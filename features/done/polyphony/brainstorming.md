# Polyphony Feature Brainstorming

## End Goal
- Support up to 4 voices (tone series) playing simultaneously.
- Ability to independently run each series through its own transform pipeline.
- Ability to apply transformations uniformly across all 4 series.

## Strategy
- **Plan** for an N-voice architecture now (up to 4 or more voices).
- **Build and test** with just 2 voices in the next iteration to prove the concept.

## Architectural Shifts

### 1. Data Structure Shift
Currently, the pipeline operates on a single `List[Tone]`. We will need a higher-level abstraction:
- **`Voice`**: Holds a single `List[Tone]`.
- **`Score`**: Holds a `List[Voice]`.

### 2. Pipeline Orchestration
To support independent and uniform transforms:
- **Independent:** The pipeline runner needs to specify *which* voice to target.
- **Uniform:** Loop over all voices in the `Score` and pass each one's tone list through the same transform pipeline.

### 3. Audio Mixing (`wav_writer.py`)
This is where the actual polyphony happens. Currently, `save_score_to_wav` concatenates tones end-to-end. The new logic will need to:
- Generate the full sequential `numpy` array for each individual voice.
- Pad shorter voices with silence (zeros) so all voices are the same length.
- Mathematically sum the `numpy` arrays together (mixing).
- Normalize the summed array before converting to 16-bit integer so the audio doesn't clip when multiple tones play at once.

### 4. CLI Complexity
Figuring out how a user specifies independent pipelines via terminal arguments will require thought.
- Example challenge: `--voice 1 440 880 --transform reverse --voice 2 523 --transform scale-duration 2.0`.

## Iterative Implementation Plan

### Iteration 1: Core Mixing Logic (Audio Backend)
- **Goal:** Prove we can mix multiple sequences of tones into a single audio file without clipping.
- **Action:** Modify `audio_io/wav_writer.py` to accept multiple tone sequences instead of a single sequence.
- **Action:** Implement logic to generate `numpy` arrays for each sequence, pad shorter sequences with silence to match the longest sequence, sum the arrays, and normalize the result to fit within 16-bit PCM bounds.
- **Test:** Write a dedicated unit test passing hardcoded multiple tone lists to the I/O function to verify output shape and normalization.

### Iteration 2a: Core Data Structures
- **Goal:** Formalize the new abstractions without breaking the existing pipeline.
- **Action:** Create a `Voice` class in `src/core/voice.py` that wraps a `List[Tone]`.
- **Action:** Create a `Score` class in `src/core/score.py` that wraps a `List[Voice]`.
- **Test:** Write simple unit tests (`test_voice.py` and `test_score.py`) to verify initialization and basic properties.

### Iteration 2b: I/O Refactoring
- **Goal:** Shift the audio writer to use the new domain models instead of raw nested lists.
- **Action:** Modify `save_score_to_wav` in `src/audio_io/wav_writer.py` to accept a `Score` object.
- **Test:** Update any mocked I/O assertions in `test_main.py` to expect a `Score` object rather than nested lists.

### Iteration 2c: App Orchestration Integration
- **Goal:** Wire the application to utilize the new structures at the boundary layer.
- **Action:** Update `run_tone_generator` in `src/main.py` so that it wraps the final tone list into a `Voice`, wraps that voice into a `Score`, and passes it to `save_score_to_wav`.

### Iteration 3a: Score-Level Global Pipeline
- **Goal:** Allow the existing pipeline to process a full `Score` uniformly.
- **Action:** Update `run_pipeline` to accept a `Score` and a list of transforms, applying those transforms to every `Voice` in the score.
- **Test:** Update `test_run_pipeline_isolation` to pass a `Score` and verify the transforms are applied to all voices within it.

### Iteration 3b: Voice-Specific Pipeline Orchestration
- **Goal:** Allow independent pipelines for individual voices.
- **Action:** Modify the orchestration logic to accept a mapping of voice indices to their specific transform lists.
- **Test:** Write new unit tests to ensure that a transform mapped to Voice 0 does not affect Voice 1.

### Iteration 4a: CLI Argument Splitting
- **Goal:** Intercept and group command-line arguments by voice before standard parsing.
- **Action:** Create a pre-parsing step in `main.py` that splits the raw CLI arguments using a new `--voice` delimiter, yielding a list of independent argument groups.
- **Test:** Write unit tests to verify the splitting logic correctly isolates frequencies and flags into separate groups for each voice.

### Iteration 4b: Multi-Voice Orchestration
- **Goal:** Connect the parsed argument groups to the `Score` and pipeline.
- **Action:** Update `process_tones` to iterate over each argument group, constructing multiple `Voice` objects and building the transform pipeline accordingly.
- **Test:** Update end-to-end CLI tests to verify commands with multiple `--voice` flags successfully produce a polyphonic `Score`.
