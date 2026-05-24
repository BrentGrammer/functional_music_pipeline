# Functional Music Pipeline

Inspired by Stephen Wolfram's concept of computational irreducibility and the iterative cyclic processes found in nature (e.g., geological processes), this application provides a framework for musical exploration. The core idea is to build complex, unpredictable, and often surprising musical structures by piping simple melodic motifs through a functional-style pipeline of algorithmic transformations.

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

Transforms are functions that modify a sequence of tones. Many can be applied at both phrase and score scope using the same public name (for example, `transpose` inside either `transforms` or `score_transforms`).

When a transform uses `params`, `params` must be an object with named fields.

#### Pitch & Harmony

- **`transpose`**: Shifts pitch up or down by `semitones`. Accepts fractions for microtonal shifts (e.g., `0.5`).
- **`invert`**: Flips the melodic contour of a phrase around a central pitch. Optionally accepts `dimension`.
- **`scale`**: Multiplies the `frequency`, `duration`, or `amplitude` of each tone by `factor` for a chosen `dimension`.

#### Basic Phrase Shaping

- **`reverse`**: Reverses the order of tones in a phrase.
- **`delay`**: Convenience alias for `pad_silence` at `position: "start"`. Use `seconds` to describe the silent duration.
- **`repeat`**: Repeats the tones in a phrase `count` times.
- **`pad_silence`**: Canonical silence-padding transform. Adds a block of silence to the beginning or end of a phrase or score using `seconds` and `position`.
- **`drift`**: Creates a linear change (e.g., accelerando, crescendo) in a chosen `dimension` using `rate` (a decimal value).

#### Tempo

- **`accelerando`**: Speeds up the phrase using `strength` (`"subtle"`, `"moderate"`, `"dramatic"`, or a numeric `0.0`–`1.0`). An optional `jaggedness` parameter (`"none"`, `"light"`, `"moderate"`, `"heavy"`, or numeric) adds stochastic variation.
- **`ritardando`**: Slows down the phrase using `strength` (`"subtle"`, `"moderate"`, `"dramatic"`, or a numeric `0.0`–`1.0`). An optional `jaggedness` parameter (`"none"`, `"light"`, `"moderate"`, `"heavy"`, or numeric) adds stochastic variation.

#### Proportion & Counterpoint

- **`golden_ratio`**: Phrase-scope Golden Ratio transform. Scales the phrase it is applied to by the Golden Ratio and optionally accepts `dimension`.
  - **`phrase_relative_golden_ratio_grow`**: Grows the phrase it is applied to in proportion to the immediately previous phrase in the same voice using the Golden Ratio. Accepts `dimension` as a parameter.
  - **`phrase_relative_golden_ratio_shrink`**: Shrinks the phrase it is applied to in proportion to the immediately previous phrase in the same voice using the Golden Ratio. Accepts `dimension` as a parameter.
- **`score_golden_ratio_shrink`**: Score-scope Golden Ratio transform. Scales each voice independently by `1 / GOLDEN_RATIO` across the selected `dimension`.
- **`score_golden_ratio_grow`**: Score-scope Golden Ratio transform. Scales each voice independently by `GOLDEN_RATIO` across the selected `dimension`.
  - NOTE on Score Transform versions of the Golden Ratio transforms:
    - If the phrase is not the first phrase in its voice, it uses the immediately previous phrase in the same voice.
    - If it is the first phrase in a later voice, it uses the entire previous voice flattened across all of that voice’s phrases.
    - If it is the first phrase of the first voice, there is no reference material, so the transform raises.
- **`feigenbaum_sequence`**: Applies the Feigenbaum constant proportionally and optionally accepts `dimension`.
- **`add_pedal_tone`**: A fugal technique that adds a sustained anchor note to the score. Requires only `frequency` (Hz). Duration is derived automatically from the longest voice in the score.
- **`stretto`**: A fugal technique that creates overlapping, imitative entries of a motif using `motif`, `num_times`, and `spacing`.

#### Complexity

These transforms derive modulation from fractals, cellular automata, or other complex-systems processes. They modulate a musical dimension (`frequency`, `duration`, or `amplitude`) using `dimension`.

- **`weierstrass`**: A smooth, self-similar fractal wobble. Accepts `dimension` and `intensity` (`"low"`, `"medium"`, `"high"`, or `"extreme"`). The intensity preset controls both the deviation amount and texture characteristics.
- **`cellular_automata`**: A binary modulation derived from an elementary cellular automaton. Accepts `dimension`, `rule` (Wolfram rule number 0–255, e.g. `30`, `90`, `110`), and `max_deviation`. The initial automaton state is derived from the input tones themselves — no randomness involved.
- **`random_drop`**: Random downward deviations at a controlled rate. Accepts `dimension`, `max_drop_pct` (how severe each drop is, 1–100), and `drop_frequency_pct` (what percentage of tones are affected, 1–100).

  ```json
  "transforms": [
    {
      "name": "weierstrass",
      "params": {
        "dimension": "frequency",
        "intensity": "medium"
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
- **`fragment`**: Turns a phrase into a damaged, ruin-like version of itself, reminiscent of the damaged, incomplete rock formations in the Southeast, by selecting random adjacent tone chunks and damaging those selected tones. It preserves the original phrase timeline: removed tones become silence, and shortened tones are followed by trailing silence.

  Params:

  - `damage_pct`: Required integer from `0` to `100`. Controls how many original tone positions are damaged. Any nonzero value damages at least one tone when the phrase is not empty.
  - `damage_tones_chunk_size`: Required integer of at least `1`. Controls the normal width (number of adjacent tones) of each damaged adjacent chunk. If the remaining damage budget is smaller than this value, the final chunk is smaller so `damage_pct` still wins.
  - `dimension`: Optional. Supported values are `"frequency"`, `"duration"`, and `"amplitude"`. If omitted, selected tones use multi-dimensional stochastic damage.
  - `repeatable_damage_key`: Optional string. Reuses the same stochastic damage pattern for the same input and params. If omitted, each run is non-deterministic.

  With `dimension` omitted, each selected tone is damaged stochastically:

  - Some selected tones are removed and replaced with silence.
  - Some selected tones are shortened and followed by trailing silence.
  - Some selected tones are softened by reducing amplitude.
  - A selected tone may receive duration damage, amplitude damage, or both.

  ```json
  "transforms": [
    {
      "name": "fragment",
      "params": {
        "damage_pct": 40,
        "damage_tones_chunk_size": 3,
        "repeatable_damage_key": "damage-pattern-a"
      }
    }
  ]
  ```

  With `dimension` provided, the selected tones are damaged only in that dimension:

  ```json
  "transforms": [
    {
      "name": "fragment",
      "params": {
        "damage_pct": 40,
        "damage_tones_chunk_size": 3,
        "dimension": "duration",
        "repeatable_damage_key": "duration-damage-a"
      }
    }
  ]
  ```

  Dimension behavior:

  - `"frequency"` replaces selected tones with silence for their original duration.
  - `"duration"` shortens selected tones and adds trailing silence so the phrase does not compress.
  - `"amplitude"` lowers selected tone amplitudes without changing pitch or duration.

- **`frost_effect`**: Simulates freeze-thaw expansion which occurs in hoodoo formation in southest Utah by appending polyphonic frost blooms to the score. Each audible tone in the input score becomes its own local frost seed. Accepts `iterations` (non-negative integer, `0` is a no-op) and optional `sustain_notes` (boolean, defaults to `false`).
  - With `sustain_notes: false`, generated frost notes keep their normal staggered durations. With `sustain_notes: true`, generated frost notes durations within each local frost bloom are extended so they all share the same end time in that generation.
  ```json
  "score_transforms": [
    {
      "name": "frost_effect",
      "params": { "iterations": 3, "sustain_notes": true }
    }
  ]
  ```
- **`terraced_drift`**: A quantized random walk that moves in discrete plateaus. Accepts `dimension` and `max_step_change_pct` (maximum percentage each tone can change from the previous, 1–100).

## Development

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
# for ai agent to use (prints in cli)
pytest --cov=. --cov-report=term-missing -q
# target a module:
pytest --cov=<package.module> --cov-report=term-missing -q
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

### MCP Tooling

#### Exa (web search MCP)

See [Setup for different CLIs](https://github.com/exa-labs/exa-mcp-server)

- For codex: `codex mcp add exa --url https://mcp.exa.ai/mcp`
- Gemini, exists in `.gemini/settings.json`
- Opencode lists it in `opencode.json` config

#### Serena

- run directly from git without manually installing:

  ```json
  // .gemini/settings.json
  "serena": {
    "command": "uv",
    "args": [
      "tool",
      "run",
      "--from",
      "git+https://github.com/oraios/serena",
      "serena",
      "start-mcp-server",
      "--context",
      "ide",
      "--project",
      "."
    ],
    "trust": true,
    "timeout": 120000
  }
  ```

  ### Docker Sandbox
  - remove policies with `sbx policy rm network --id c4164c09-b43e-429e-a528-ceb034d63028` (don't include the local: or prepended string with the id)
