# Composition And Score Document Schema

## Decision

A composition is the saved user-facing object. It owns metadata and contains a score.

A score is the musical blueprint: motifs, voices, phrases, transforms, and timing. The current JSON shape in `compositions/*.json` represents a score and should move under a `score` property in the composition document.

Use the new shape directly. Do not preserve backwards compatibility for the old document shape because the app is not yet used by external users.

## Target Shape

```json
{
  "name": "Frost bloom study",
  "description": "Optional notes about the composition.",
  "score": {
    "motifs": {},
    "voices": [],
    "score_transforms": []
  }
}
```

The `score` object replaces the old top-level `motifs` plus `composition` structure.

Old shape:

```json
{
  "description": "...",
  "motifs": {},
  "composition": {
    "voices": [],
    "score_transforms": []
  }
}
```

New shape:

```json
{
  "name": "...",
  "description": "...",
  "score": {
    "motifs": {},
    "voices": [],
    "score_transforms": []
  }
}
```

## Implementation Notes

- Add `ScoreDocumentInput` and `ScoreDocument` schema types for the musical content.
- Update `CompositionDocumentInput` and `CompositionDocument` so they contain metadata plus `score`.
- Update the parser so `generate_score_plan` reads `document["score"]` instead of top-level `motifs` and `composition`.
- After the score shape migration is stable, expand `_validate_composition_document()` to validate composition metadata fields as part of the top-level document contract.
- Keep the existing runtime `Score` domain object. It remains the parsed/renderable domain model.
- Update existing JSON files in `compositions/` to the new shape.
- Update parser, loader, CLI, and tests to use the new document shape.
- Tests that need file input should define that document inside the test and write it to a temporary file instead of depending on checked-in composition JSON fixtures.
- Do not add compatibility logic for the old shape.

## Naming Model

- Composition: saved user object and API resource.
- Score document: editable musical blueprint stored inside the composition.
- Score domain object: runtime model produced from the score document for transforms/rendering.
- Render/export: generated WAV, MP3, or MIDI artifact.

1. Migrate schema
   - Add ScoreDocumentInput / ScoreDocument.
   - Update CompositionDocumentInput / CompositionDocument to contain metadata plus score.
   - New shape:

   ```json
   {
     "name": "...",
     "description": "...",
     "score": {
       "motifs": {},
       "voices": [],
       "score_transforms": []
     }
   }
   ```

2. Update parser
   - generate_score_plan reads document["score"].
   - Remove old document["motifs"] + document["composition"] parsing.
   - No backwards compatibility.
3. Stabilize score-shape coverage
   - Update parser/schema/loader/render tests to use the new document shape.
   - Prefer test-local documents and temporary files over checked-in JSON fixtures for tests.
4. Validate composition metadata
   - Expand `_validate_composition_document()` to validate top-level metadata fields.
   - Validate `name` as a required non-empty string.
   - Validate `description` as a string when present.
5. Update composition JSON examples
   - Convert files in compositions/ to the new shape.
6. Add metadata validation tests
   - Add focused parser tests for valid and invalid metadata combinations.
7. Run targeted then full tests
   - Start with parser/loader/render tests.
   - Then broader suite.

## Handoff

Current state:

- The composition document now requires `name`.
- `created_at` is no longer part of the composition document contract.
- `score` is nested under the composition document and is the only place where motifs, voices, and score transforms live.
- `composition/parser.py`, `composition/schema.py`, and the focused parser/loader/document tests have already been migrated to the new shape.

What remains:

- Update `tests/test_proportion_golden_ratio.py` to the new document shape.
- Decide whether to keep or remove any remaining checked-in JSON examples under `compositions/`.
- If desired, do a final cleanup pass on this document so the implementation notes and examples match the settled contract exactly.

Useful next-session entry point:

- Start with `tests/test_proportion_golden_ratio.py`.
