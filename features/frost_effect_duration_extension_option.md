# Frost Effect Duration Extension Option

## Goal

Preserve the current frost effect sound as the default behavior, but add an explicit option for a duration-extending variant.

## Problem

The current frost effect builds new voices as discrete overlapping entries. Existing tones keep their original duration, so the texture does not stretch previous tones to fill the phrase.

## Desired Behavior

- Keep the current frost effect behavior unchanged by default.
- Add either:
  - an option on the existing frost effect transform, or
  - a separate transform dedicated to duration extension.
- The duration-extending mode should stretch earlier tones so they last through the full evolving phrase or event window.

## Notes

- The new behavior should be opt-in.
- The default sound should remain identical to the current frost effect output.
- This expansion should be modeled as a separate concern from the existing pitch-expansion behavior.