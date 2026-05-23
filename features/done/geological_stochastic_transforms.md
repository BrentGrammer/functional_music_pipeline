# Geological & Chaos-Driven Stochastic Transforms

## Concept & Aesthetic Vision
Instead of relying on standard smooth randomness (like Perlin noise), this feature set aims to generate stochastic variations inspired by the jagged, eroded, and highly stratified rock formations of the American Southwest (e.g., Canyonlands and Arches National Parks). 

The goal is to produce musical contours that mimic geological phenomena: mesas, plateaus, sudden sheer cliffs, deep canyons, and fractal roughness. This perfectly aligns with the project's core inspiration drawn from Chaos Theory and Stephen Wolfram's ideas of Computational Irreducibility—creating complex, unpredictable outcomes from simple iterations.

These stochastic variations can be applied across multiple dimensions of a `list[Tone]`:
- **Frequency:** Interval jumps, microtonal jaggedness, and plateaued pitches.
- **Duration:** Rhythmic snapping, sudden fermatas, and chaotic micro-timing.
- **Amplitude:** Dynamic drops, sudden loud spikes, and fractal shimmering.

## Proposed Mathematical Models

### 1. Terraced / Quantized Brownian Motion (The Layer Cake)
**Geological Analog:** Stratified rock layers, mesas, and plateaus.
**Mechanism:** Generates a 1D Random Walk (Brownian motion) but applies a rigid step-function (quantization) to the output.
**Musical Effect:** The tone property (e.g., pitch) holds steady on a "plateau" for an unpredictable amount of time, then violently snaps to a completely new, distinct layer. 

### 2. 1D Cellular Automata (Wolfram Rules)
**Geological Analog:** Complex mineral deposit structures and jagged, geometric ridge outlines.
**Mechanism:** Utilizing Elementary Cellular Automata (like Rule 30 or Rule 110) as a 1D map. 
**Musical Effect:** Translating the binary states or neighborhood patterns into modifiers creates highly structured, aperiodic, and geometrically jagged variations. It is the purest translation of "computational irreducibility" into the pipeline.

### 3. The Weierstrass Function
**Geological Analog:** Extreme fractal roughness; the grainy, infinitely jagged texture of sandstone faces.
**Mechanism:** A mathematical function that is "continuous everywhere but differentiable nowhere." No matter how closely you zoom in, the line remains spiky.
**Musical Effect:** Intense, fractal "shimmering". When applied to frequency, it creates chaotic, unpredictable micro-variations on every single note, ensuring no two tones are ever perfectly identical.

### 4. Interspersed Ridged Multifractal Drops
**Geological Analog:** Sudden, deep slot canyons and sharp solitary spires interrupting flat landscapes.
**Mechanism:** Layered octaves of noise using absolute values to flip valleys into sharp creases.
**Musical Effect:** Used as a composite layer over the Terraced or CA models. It introduces rare but extreme events—sudden, jagged drops in pitch or volume, breaking up predictable patterns with violent, canyon-like interruptions in the sonic contour.

## Iterative Implementation Plan

### Iteration 1: Dimension-Agnostic Foundation & Weierstrass Function
*Focus: Establish the `geological.py` module, the dimension selection enum, and the most atomic mathematical generator.*
1. Create `src/transforms/geological.py` and define a `ToneDimension` enum (Frequency, Duration, Amplitude).
2. Implement the pure math generator for the **Weierstrass Function** (ensuring it accepts a seed for deterministic testing).
3. Implement a generic `apply_stochastic_profile(tones, generator, dimension, intensity)` that handles the mapping logic for *any* dimension.
4. Implement `weierstrass_transform(tones, dimension, intensity, seed)` using the generic applicator.
5. Write tests in `src/tests/test_geological.py` asserting deterministic output across Frequency, Duration, and Amplitude.

### Iteration 2: Terraced / Quantized Brownian Motion
*Focus: Add stateful, stepped randomization.*
1. Implement the pure math generator for the **1D Random Walk with Quantization** in `geological.py`.
2. Implement `terraced_transform` that uses the generic applicator to map the plateau steps to the requested tone dimension.
3. Write tests verifying the "plateau" behavior across different dimensions and deterministic seeding.

### Iteration 3: 1D Cellular Automata (Wolfram Rules)
*Focus: Implement the core computational irreducibility engine.*
1. Implement a **1D Cellular Automata Generator** function that can take an initial state and a rule (e.g., Rule 30, Rule 110) and yield the next state's binary array.
2. Implement `cellular_automata_transform` that maps the binary states (0s and 1s) to the specified dimension using the generic applicator.
3. Write unit tests validating the Cellular Automata generation against known Wolfram rule outputs and dimension applications.

### Iteration 4: Interspersed Ridged Multifractal Drops
*Focus: Extreme interruptions.*
1. Implement the **Ridged Multifractal** generator (layered noise with absolute value flipping).
2. Implement `canyon_drop_transform` that overlays these sudden spikes/drops onto a `list[Tone]`'s specified dimension.
3. Write tests to ensure it only applies sparse, extreme variations rather than constant noise, across dimensions.

### Iteration 5: Integration & Orchestration
*Focus: Exposing the new tools to the user.*
1. Update `src/transforms/base.py` (`TransformDescriptor`) and the schema definitions to include the new multi-dimensional geological transforms.
2. Update the CLI parser / JSON composition parser to support these new transforms and their dimension arguments.
3. Add an integration test that runs a composition through a geological transform pipeline targeting multiple dimensions and verifies the output structure.
