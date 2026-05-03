# Functional Music Pipeline

Inspired by Stephen Wolfram's concept of computational irreducibility and the iterative cyclic processes found in nature (e.g., geological formation, crystal growth), this application provides a framework for musical exploration. The core idea is to build complex, unpredictable, and often surprising musical structures by piping simple melodic motifs through a functional-style pipeline of algorithmic transformations.

The application generates music based on a structured JSON composition file, outputting the result as either a WAV audio file or a Standard MIDI File you could import into a DAW such as Cubase.

The application automatically preserves microtonal details in MIDI exports using high-resolution pitch bend messages.

### Setup & Usage

This application is designed to be run inside a Docker container.

#### Prerequisites

- Docker
- Docker Compose

#### 1. Build and Start the Service

From your terminal, navigate to the `src` directory and run:

```bash
docker-compose up --build -d
```

This will build the Docker image and start the service in the background.

#### 2. Enter the Container

Get an interactive shell inside the running container:
```bash
docker-compose exec functional-music-pipeline bash
```

You will now have a `bash` prompt, and all subsequent commands should be run from inside the container.

#### 3. Run the Generator

From inside the container's shell, you can now run the generator script directly.

**Example:**

```bash
# To generate a WAV file (default)
python main.py --composition-file compositions/geological_example.json --output-name my_composition

# To generate a MIDI file
python main.py --composition-file compositions/microtonal_demo.json --output-name my_demo --output-format midi
```

Generated files will appear in the `output` directory on your local machine.

#### 4. Stop the Service

When you are finished, `exit` the container's shell and stop the service from your local machine:

```bash
docker-compose down
```

### Core Concepts

- **Tone**: A single sound defined by its `frequency` (Hz) and `duration` (seconds). e.g., `"440:0.5"`.
- **Voice**: A sequence of Tones, like a single melodic line. Each Voice is placed on a separate track in a MIDI file.
- **Score**: The complete composition, containing one or more Voices that play simultaneously.

### Creating a Composition File

A composition file has two main parts: `motifs` (reusable musical ideas) and `composition` (the arrangement of those motifs into voices and phrases).

```json
{
  "motifs": {
    "seed_a": ["155.56:0.3", "185.00:0.15"],
    "seed_b": ["622.25:0.2", "440:0.25"]
  },
  "composition": {
    "voices": [
      {
        "phrases": [
          {
            "motifs": ["seed_a", "seed_b"],
            "transforms": ["reverse"]
          }
        ]
      }
    ]
  }
}
```

### Available Transforms

Transforms are functions that modify a sequence of tones. Many can be applied to a single phrase or to all voices in a score (e.g., `transpose` vs. `score_transpose`).

#### Pitch & Harmony

- **`transpose`**: Shifts pitch up or down by a number of semitones. Accepts fractions for microtonal shifts (e.g., `0.5`).
- **`invert`**: Flips the melodic contour of a phrase around a central pitch.
- **`scale`**: Multiplies the `frequency`, `duration`, or `amplitude` of each tone by a factor.

#### Time & Sequence

- **`reverse`**: Reverses the order of tones in a phrase.
- **`delay`**: Adds a period of silence before each tone.
- **`repeat`**: Repeats the tones in a phrase a specified number of times.
- **`pad_silence`**: Adds a block of silence to the beginning or end of a phrase.
- **`accelerando`**: Speeds up the phrase. An optional `jaggedness` parameter adds stochastic variation.
- **`ritardando`**: Slows down the phrase. An optional `jaggedness` parameter adds stochastic variation.
- **`drift`**: Creates a linear change (e.g., accelerando, crescendo) in `frequency`, `duration`, or `amplitude`.

#### Structural & Algorithmic

- **`golden_ratio` / `feigenbaum_sequence`**: Applies mathematical constants to the properties of a phrase, creating new musical material where the relationships between notes feel organic and self-similar, much like patterns found in nature.
- **`add_pedal_point`**: A fugal technique that adds a sustained or repeated anchor note to the score, providing a harmonic foundation.
- **`stretto`**: A fugal technique that creates overlapping, imitative entries of a motif for climactic effect.

#### Geological & Stochastic Transforms

These transforms introduce structured randomness, inspired by geological patterns, to a musical dimension (`frequency`, `duration`, or `amplitude`).

- **`erosion`**: Mimics geological erosion by progressively "wearing away" a phrase. It takes a `dimension` parameter to specify what to erode.
  ```json
  "transforms": [{"name": "erosion", "params": {"dimension": "duration"}}]
  ```
- **`frost`**: Simulates the frost effect which slowly creates cracks in rock as precipitation gets into micro-crevices and oscillates between freezing and thawing to gradually widen the cracks (e.g., in hoodoos in Southeast Utah). It takes a single `iterations` parameter which indicates how many times this cyclic process happens.
  ```json
  "score_transforms": [{"name": "frost", "params": {"iterations": 3}}]
  ```
- **`geological`**: The main stochastic transform. Use it with one of the profiles below to apply different patterns of variation.

  ```json
  "transforms": [
    {
      "name": "geological",
      "params": {
        "profile": { "type": "weierstrass" },
        "dimension": "frequency",
        "max_deviation": 0.1
      }
    }
  ]
  ```

  - **`weierstrass`**: A smooth, "wobbly" fractal curve.
  - **`terraced`**: Snaps values to discrete "plateaus" with sharp jumps.
  - **`cellular_automata`**: Creates complex, aperiodic patterns from simple rules.
  - **`ridged_multifractal`**: Creates a mostly stable signal with rare, sharp drops.
  - **`random_drop`**: Injects random downward shifts at a controlled rate.
