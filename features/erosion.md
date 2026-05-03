# Feature: Erosion Transform

## Overview

The `erosion_transform` mimics the geological process of erosion, gradually wearing down a musical phrase. It operates across different dimensions (`DURATION`, `AMPLITUDE`, `FREQUENCY`), applying a specific "decay" logic appropriate to that dimension.

## Behavior by Dimension

### 1. Duration (Structural Erosion)

*   **Metaphor:** Physical weathering where the end of a structure crumbles away.
*   **Behavior:** Iteratively removes the last tone of the sequence and repeats the result until only the first tone remains.
*   **Algorithm:**
    1.  Start with the full sequence.
    2.  Remove the last tone.
    3.  Append the remaining sequence to the result.
    4.  Repeat until only one tone remains.
*   **Example:**
    *   Input: `[A, B, C]`
    *   Pass 1: `[A, B]` (C removed)
    *   Pass 2: `[A]` (B removed)
    *   Result: `[A, B, A]`

### 2. Amplitude (Volume Erosion)

*   **Metaphor:** Fading away into silence, like a sound dissipating in a large space.
*   **Behavior:** Applies a gradual decay to the amplitude of the tones. The first tone remains at full volume, while the last tone becomes silence.
*   **Algorithm:**
    1.  Let $N$ be the total number of tones.
    2.  For each tone at index $i$, calculate the scale factor: $scale = 1.0 - \frac{i}{N-1}$.
    3.  Multiply the tone's amplitude by this scale factor.
*   **Result:** A "fade out" effect where the beginning is loud and the end is silence.

### 3. Frequency (Pitch Erosion)

*   **Metaphor:** "Collapsing" or "settling", like a pile of sand settling into a flat dune.
*   **Behavior:** Gradually shifts all tones towards the frequency of the first tone.
*   **Algorithm:**
    1.  Target frequency = frequency of the first tone ($T_0$).
    2.  For each subsequent tone, interpolate its frequency closer to $T_0$.
    3.  The last tone becomes the same frequency as the first.
*   **Result:** A melody that "crumbles" or "glides" into a single repeated pitch.

## Implementation Plan

### Step 1: Refactor Function Signature
Update `erosion_transform` in `src/transforms/erosion.py` to accept an optional `dimension` parameter (defaulting to `DURATION`). Import `ToneDimension` from `transforms.base`.

### Step 2: Implement Duration Logic
Extract the current "structural erosion" logic into a private helper function `_erode_duration`. Update the main function to call this helper when the dimension is `DURATION`.

### Step 3: Implement Amplitude Logic
Create a private helper function `_erode_amplitude` that implements the linear fade-out algorithm. Update the main function to handle the `AMPLITUDE` dimension.

### Step 4: Implement Frequency Logic
Create a private helper function `_erode_frequency` that implements the pitch collapse algorithm. Update the main function to handle the `FREQUENCY` dimension.

### Step 5: Write Tests
Add unit tests to `src/tests/test_erosion.py` (new file) to verify the behavior for all three dimensions.

### Step 6: Verify Integration
Run `python -m pytest` to ensure all tests pass and the feature works as expected.
