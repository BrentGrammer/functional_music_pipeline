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
  "document_version": 1,
  "created_at": timestamp,
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
  "document_version": 1,
  "created_at": timestamp,
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
- Keep the existing runtime `Score` domain object. It remains the parsed/renderable domain model.
- Update existing JSON files in `compositions/` to the new shape.
- Update parser, loader, CLI, and tests to use the new document shape.
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
     "document_version": 1,
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
3. Update composition JSON examples
   - Convert files in compositions/ to the new shape.
4. Update tests
   - Parser/schema/loader/render tests should use the new document shape.
   - Keep behavior expectations the same: same score output, same transforms, same renders.
5. Run targeted then full tests
   - Start with parser/loader/render tests.
   - Then broader suite.
