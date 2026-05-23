## Clarify Phrase-Relative Reference Scope

### Summary

The current phrase-relative Golden Ratio behavior is musically useful but conceptually overloaded.

`phrase_relative_golden_ratio_shrink` and `phrase_relative_golden_ratio_grow` do not always reference the same kind of musical object:

- If the current phrase is not the first phrase in its voice, they reference the immediately previous phrase in the same voice.
- If the current phrase is the first phrase of a later voice, they reference the entire previous voice flattened across all of its phrases.
- If the current phrase is the first phrase of the first voice, they raise because no reference material exists.

This changing reference unit makes the transform harder to reason about from its name alone.

### Problem

The transform name implies "previous phrase", but in one structural case it silently means "previous voice".

That creates a few problems:

- The user cannot tell from the transform name alone what will happen on the first phrase of a later voice.
- The reference unit changes based on score position instead of explicit configuration.
- The behavior is usable, but it is surprising enough that it needed a dedicated demo and explanation.

### Current Behavior

- Same voice, later phrase:
  - Use the immediately previous phrase in the same voice.
- Later voice, first phrase:
  - Use the entire previous voice flattened to tones.
- First voice, first phrase:
  - Raise because no reference exists.

### Why This Matters

This behavior is not just an implementation detail. It changes the musical result substantially:

- referencing a previous phrase is local and phrase-oriented
- referencing an entire previous voice is broader and polyphonic in meaning

Those are both valid musical ideas, but they are not the same idea.

### Preferred Solution

Add an explicit `reference_scope` parameter to the phrase-relative Golden Ratio transforms.

Example:

```json
{
  "name": "phrase_relative_golden_ratio_shrink",
  "params": {
    "dimension": "duration",
    "reference_scope": "previous_phrase"
  }
}
```

And:

```json
{
  "name": "phrase_relative_golden_ratio_shrink",
  "params": {
    "dimension": "duration",
    "reference_scope": "previous_voice"
  }
}
```

### Proposed Semantics

- `reference_scope: "previous_phrase"`
  - Use only the immediately previous phrase in the same voice.
  - Raise if the current phrase is the first phrase in its voice.
- `reference_scope: "previous_voice"`
  - If the current phrase is the first phrase of a later voice, use the entire previous voice.
  - If the current phrase is not the first phrase in its voice, still use the immediately previous phrase in the same voice.

This preserves the musically useful fallback while making the choice explicit in the API.

### Alternative Solutions

#### Option 1: Separate transform names

Introduce explicit transforms such as:

- `phrase_relative_golden_ratio_shrink`
- `previous_voice_golden_ratio_shrink`
- `phrase_relative_golden_ratio_grow`
- `previous_voice_golden_ratio_grow`

Pros:

- very explicit API
- no ambiguity at call sites

Cons:

- more transform names in the registry
- larger public API surface

#### Option 2: Always raise on the first phrase of every voice

Remove the cross-voice fallback entirely.

Pros:

- simplest mental model
- phrase-relative always means phrase-relative

Cons:

- removes a musically useful behavior
- exact equivalent cannot currently be reconstructed cleanly with existing composition mechanisms while preserving onset placement

### Recommendation

Prefer the `reference_scope` parameter.

Reasoning:

- it keeps the current useful musical behavior available
- it removes the ambiguity from the transform contract
- it adds only a small amount of code and API complexity compared to adding multiple new transform names
- it scales better if other relative transforms need the same distinction later

### Implementation Notes

- Extend `GoldenRatioParams` with `reference_scope`.
- Extend `GOLDEN_RATIO_PARAMS_SPEC` with an enum/string field.
- Replace direct use of the current implicit lookup with a small reference resolver.
- Update demos and tests so both scopes are explicit and observable.
