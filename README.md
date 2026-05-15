# Functional Music Pipeline

Inspired by Stephen Wolfram's concept of computational irreducibility and the iterative cyclic processes found in nature (e.g., geological formation, crystal growth), this application provides a framework for musical exploration. The core idea is to build complex, unpredictable, and often surprising musical structures by piping simple melodic motifs through a functional-style pipeline of algorithmic transformations.

The application generates music based on a structured JSON composition file, outputting the result as either a WAV audio file or a Standard MIDI File you could import into a DAW such as Cubase.

The application automatically preserves microtonal details in MIDI exports using high-resolution pitch bend messages.

### Setup & Usage

This application is designed to be run inside a Docker container.

#### Prerequisites

- Docker
- Docker Compose (comes with Docker Desktop)

#### 1. Build and Start the Service

From your terminal, navigate to the `src` directory and run:

```bash
docker-compose up --build -d
```

This will build the Docker image and start the service in the background.

#### 2. Enter the Container

Get an interactive shell inside the running container:

```bash
# to get the container name:
docker ps
# Shell into the container:
docker-compose exec -it <container_name> bash
```

You will now have a `bash` prompt, and all subsequent commands should be run from inside the container.

#### 3. Run the Application

From inside the container's shell, you can now run the generator script directly.

**Example:**

```bash
# To generate a WAV file (default)
python main.py --composition-file compositions/geological_example.json --output-name my_composition

# To generate a MIDI file
python main.py --composition-file compositions/microtonal_demo.json --output-name my_demo --output-format midi

# Get output for all files in the compositions folder:
for file in compositions/*.json; do
  name="$(basename "$file" .json)"
  python main.py --composition-file "$file" --output-name "$name"
done
```

Generated files will appear in the `output` directory on your local machine.

#### 4. Stop the Service

When you are finished, `exit` the container's shell and stop the service from your local machine:

```bash
docker-compose down
```

### Core Concepts

- **Motif**: A reusable musical idea defined as a sequence of tones. Motifs are the building blocks of a composition and can be referenced by name in phrases.
- **Tone**: A single sound defined by its `frequency` (Hz) and `duration` (seconds). e.g., `"440:0.5"`.
- **Phrase**: A sequence of Tones played one after the other. Monophonic in nature.
- **Voice**: Contains one or more phrases. Voices are polyphonic in nature and can played at the same time.
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
            "transforms": [
              {
                "name": "reverse"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Available Transforms

Transforms are functions that modify a sequence of tones. Many can be applied to a single phrase or to all voices in a score (e.g., `transpose` vs. `score_transpose`).

When a transform uses `params`, `params` must be an object with named fields.

#### Pitch & Harmony

- **`transpose`**: Shifts pitch up or down by `semitones`. Accepts fractions for microtonal shifts (e.g., `0.5`).
- **`invert`**: Flips the melodic contour of a phrase around a central pitch. Optionally accepts `dimension`.
- **`scale`**: Multiplies the `frequency`, `duration`, or `amplitude` of each tone by `factor` for a chosen `dimension`.

#### Basic Phrase Shaping

- **`reverse`**: Reverses the order of tones in a phrase.
- **`delay`**: Adds a period of silence before each tone. Use `seconds` to describe the silent duration.
- **`repeat`**: Repeats the tones in a phrase `count` times.
- **`pad_silence`**: Adds a block of silence to the beginning or end of a phrase using `seconds` and `position`.
- **`drift`**: Creates a linear change (e.g., accelerando, crescendo) in a chosen `dimension` using `rate`.

#### Tempo

- **`accelerando`**: Speeds up the phrase using `strength`. An optional `jaggedness` parameter adds stochastic variation.
- **`ritardando`**: Slows down the phrase using `strength`. An optional `jaggedness` parameter adds stochastic variation.

#### Proportion & Counterpoint

- **`golden_ratio` / `feigenbaum_sequence`**: Applies mathematical constants to a phrase. Both optionally accept `dimension`.
- **`add_pedal_point`**: A fugal technique that adds a sustained or repeated anchor note to the score. It requires `frequency` and `duration`, and may also use `amplitude`, `mode`, and `pulse_duration`.
- **`stretto`**: A fugal technique that creates overlapping, imitative entries of a motif using `motif`, `num_times`, and `spacing`.

#### Complexity

These transforms derive modulation from fractals, cellular automata, or other complex-systems processes. They modulate a musical dimension (`frequency`, `duration`, or `amplitude`) using `dimension` and `max_deviation`.

- **`weierstrass` / `score_weierstrass`**: A smooth, self-similar fractal wobble. Accepts `dimension`, `max_deviation`, and optional `seed`, `amplitude_scaling`, `ripples_per_wave`, and `iterations`.
- **`cellular_automata` / `score_cellular_automata`**: A binary modulation derived from an elementary cellular automaton. Accepts `dimension`, `max_deviation`, and optional `rule`, `seed`, and `width`.
- **`random_drop` / `score_random_drop`**: Random downward deviations at a controlled rate. Accepts `dimension`, `max_deviation`, and optional `seed` and `drop_rate`.

  ```json
  "transforms": [
    {
      "name": "weierstrass",
      "params": {
        "dimension": "frequency",
        "max_deviation": 0.1,
        "seed": 42
      }
    }
  ]
  ```

#### Geological

These transforms use geological metaphors or landform-inspired motion. Some reshape phrase structure directly, while others modulate a musical dimension (`frequency`, `duration`, or `amplitude`).

- **`erosion`**: Mimics geological erosion by progressively "wearing away" a phrase. It takes a `dimension` parameter to specify what to erode.
  ```json
  "transforms": [{"name": "erosion", "params": {"dimension": "duration"}}]
  ```
- **`frost_effect`**: Simulates the frost effect which slowly creates cracks in rock as precipitation gets into micro-crevices and oscillates between freezing and thawing to gradually widen the cracks (e.g., in hoodoos in Southeast Utah). It optionally accepts `iterations`.
  ```json
  "score_transforms": [{"name": "frost_effect", "params": {"iterations": 3}}]
  ```
- **`terraced_drift` / `score_terraced_drift`**: A quantized random walk that moves in discrete plateaus. Accepts `dimension`, `max_deviation`, and optional `seed`, `step_size`, and `quantize_resolution`.
- **`ridged_drop` / `score_ridged_drop`**: A mostly stable signal interrupted by occasional sharp drops, like a geological ridgeline. Accepts:
  - `dimension` (required): The musical dimension to modulate (`frequency`, `duration`, or `amplitude`).
  - `drop_depth` (required): How far the dimension can fall. Either a named preset (`none`, `low`, `medium`, `high`, `extreme`) or a numeric value from `0.0` to `1.0`.
  - `intensity` (optional): Controls the density and aggressiveness of the drop pattern. One of `subtle`, `medium` (default), or `severe`.
  - `new_pattern_each_use` (optional): When `true`, each use of this transform generates a new random drop pattern. When `false` (default), the same pattern is used for reproducibility.

  ```json
  "transforms": [
    {
      "name": "ridged_drop",
      "params": {
        "dimension": "amplitude",
        "drop_depth": "high",
        "intensity": "severe",
        "new_pattern_each_use": true
      }
    }
  ]
  ```

### Development

All developer commands should be run from inside the running Docker container.

#### Linting (Ruff)

To check the code for style and formatting issues, run:

- `ruff check .` Then fix with `ruff check . --fix` or manually.

#### Type Checking (MyPy)

To perform static type checking, run:

```bash
mypy .
```

#### Check for unused functions and variables

```bash
vulture . --exclude "*test*.py,tests/,.venv/"
```

#### Testing (Pytest)

To run the full test suite, execute:

```bash
pytest tests
```

#### Test Coverage

- Use the pytest coverage tool.

```bash
pytest --cov=. tests
# html report
pytest --cov=. --cov-report=html tests/
# txt
pytest --cov=. tests/ > coverage.txt
```

#### Cyclomatic Complexity Analysis

- use the installed dev dependency tool `radon`
  - You can pinpoint functions with a high complexity score and ask a coding agent to refactor these to reduce the Cyclomatic Complexity.
- `radon cc ./ -a -s`
- Add a minimum score by appending the class: `radon cc ./ -a -s -n C -e "tests/*,*/tests/*,test/*,*/test/*"`
```shell
A = 1–5
B = 6–10
C = 11–20
D = 21–30
E = 31–40
F = 41+
```

### Generating a dependency graph

- Uses pydeps package
- `pydeps main.py --show-dot --noshow --max-module-depth 3 -x os re sys numpy | sed 's/ \[.*\]//g' > readonly/dependency_graph.dot`
