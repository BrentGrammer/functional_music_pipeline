# Frost Phrase Scope Plan

## Problem
The `frost` effect currently works only as a score-level transform, but the demo in `compositions/frost_effect_demo.json` tries to use it inside a phrase. The parser and transform registry do not currently support that shape.

## Goal
Allow frost to work in both places:

* score scope, where it appends new frost voices to the full score
* phrase scope, where it can be applied to a phrase and still produce the expected frost expansion in the surrounding score

## Current Constraints

* `frost_effect` is registered as `TransformScope.SCORE` in `composition/parser.py`
* phrase transforms currently operate on `list[Tone]` and return `list[Tone]`
* frost is polyphonic, so a phrase-level application cannot be represented cleanly by the current phrase transform contract

## Proposed Approach

1. Keep the existing score-level `frost_effect` behavior intact.
2. Add a phrase-scoped frost entry point that reuses the same underlying frost logic.
3. Extend phrase parsing so a transform can contribute auxiliary voices, not just modified tones.
4. Preserve phrase position inside the voice by offsetting any frost-generated voices to the phrase start time.
5. Update demos and tests so both usage modes are explicit and covered.

## Implementation Steps

1. Add a phrase-level frost wrapper in `transforms/frost.py`.
   * Reuse `frost_effect` so score-level and phrase-level frost stay behaviorally aligned.
   * Give the phrase wrapper a name that is valid in phrase scope, such as `frost`.

2. Extend the parser to support phrase expansion results.
   * Introduce an internal result shape that can carry:
     * the phrase's primary tones
     * any extra voices created by the transform
   * Keep ordinary phrase transforms unchanged when they do not expand into voices.

3. Update voice assembly in `composition/parser.py`.
   * Track phrase start times while building a voice.
   * When a phrase transform produces extra voices, shift them by the current phrase offset before adding them to the score.

4. Decide on the public names.
   * Phrase scope: `frost`
   * Score scope: keep `frost_effect`
   * Optional future cleanup: add a score-scoped alias if the JSON API should be more consistent

5. Add tests.
   * phrase-level frost is accepted by the parser
   * phrase-level frost produces auxiliary voices
   * auxiliary voices begin at the correct phrase offset
   * score-level frost still works as before
   * invalid `iterations` values still raise clear errors

6. Update docs and demos.
   * Fix `compositions/frost_effect_demo.json` so it uses the phrase-scoped name if that demo is meant to live inside a phrase
   * Update the README examples so the documented JSON matches the supported scope

## Notes

This is not just a registry rename. Phrase-level frost needs parser support for polyphonic expansion, because the transform does not merely alter a tone sequence; it creates new concurrent voices.
