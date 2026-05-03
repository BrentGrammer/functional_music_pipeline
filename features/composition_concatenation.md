# Composition Concatenation

## Goal

Allow the user to pass multiple composition files on the CLI and render them as one combined output.

The intended behavior is sequential concatenation:

- load each composition file in the order provided
- parse each file into a `Score`
- append the compositions in sequence
- export one final WAV or MIDI file

This feature is meant to build longer works from shorter compositions without requiring the user to manually merge the JSON files.

## CLI Shape

The repeated-argument form is the preferred API:

```bash
python main.py \
  --composition-file intro.json \
  --composition-file development.json \
  --composition-file coda.json \
  --combine-mode concat \
  --output-name suite \
  --output-format midi
```

Defaults should still work:

```bash
python main.py \
  --composition-file intro.json \
  --composition-file coda.json
```

That should render to:

```text
output/output.wav
```

## Semantics

The combined output should preserve ordering. The first composition comes first, followed by the second, then the third, and so on.

This should not merge unrelated compositions into one simultaneous score unless that is explicitly chosen later. The first version should be sequential concatenation only.

## Combination Modes

Use `--combine-mode` to choose how the compositions are merged:

- `concat`: play each composition one after another
- `layer`: play all compositions at the same time

The default should be `concat`, since sequential concatenation is the safest and most predictable behavior.

## Implementation Notes

The existing architecture already supports exporting a `Score` to both WAV and MIDI, so the main work is at the CLI and orchestration boundary:

1. Accept multiple `--composition-file` arguments.
2. Add `--combine-mode` with `concat` as the default.
3. Load each file into its own `Score`.
4. Combine the scores according to the selected mode.
5. Pass the combined result to the existing export path.

## First Iteration

The first version should focus on the simplest usable behavior:

- repeated `--composition-file`
- `--combine-mode concat|layer`
- sequential concatenation
- optional layering
- no changes to WAV or MIDI export logic
- no changes to the existing `--output-name` and `--output-format` API
