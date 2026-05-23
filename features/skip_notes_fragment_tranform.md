# Fragment Transform

- A transform that turns a melody or phrase into a fragment with randomly missing notes or pieces.
- Similar to an ancient Ruin which once was whole, but now is missing pieces and fragmented.
- Reminiscent of broken, jagged fragmented rock formations such as those in Castle Valley in Utah.

## Desired Behavior

- A Phrase has random parts of it removed:
  - Frequency
    - random tones are removed replacing them with silence
    - density/intensity/destruction_level/fragmentation_strength/damage_level? How much of the phrase is chipped away?
    - damage_portion_size/fracture_region_size/fracture_size/fragment_span/damage_region_span/fragment_region_span_size? - how many notes to remove at one time - we should be able to remove larger chunks sometimes instead of a single note.
  - Duration
    - the duration of notes is randomly shortened to various degrees
    - By how much? Probably by some bounded amount, but each duration reduction should also be stochastic and not uniform across all the randomly selected notes to reduce.
    - Every note or pick random selection? Probably initial sweep to select random notes, then apply the fragmentation to the dimension on those randomly selected notes from the phrase.
  - Amplitude
    - Random selected tones have their amplitude drastically reduced and modified to be softer. (always taking away, so we don't increase)

### Stochastic Combination of Fragmentation on Dimensions

- A stochastic combination of fragmenting all three dimensions could be an additional option
  - The implementation might use “fracture regions” instead of independent random selection. For example, choose 2-5 random spans across the phrase, then
    inside each span remove some notes, shorten others, and soften others. That would better resemble chunks missing from a larger structure while still preserving
    fragments of the original motif.

The multi-dimensional behavior could work like this:

1. Select damaged notes using patchy clusters.
   - damage_pct=40 means choose roughly 40% of the notes.
   - tones_per_fragment=4 means damaged areas tend to appear in irregular runs in 4 note spans, unless the damage percent dictates that we cannot damage that many notes to adhere to it.
   - Selection keeps trying random patch starts and random patch lengths until the target damage count is reached.
2. For each selected note, apply stochastic chips.
   - First, roll for full drop.
   - If dropped, replace the note with silence of the same duration.
   - If not dropped, independently roll for duration shortening and amplitude softening.
   - A note can be both shortened and softened.
   - Full drop wins because frequency removal means the whole note is missing.
3. Preserve the original phrase timeline.
   - Dropped notes become rests.
   - Shortened notes should probably become “short note + trailing silence” so the phrase does not compress.
   - This makes holes audible as missing structure rather than just faster rhythm.

```python
fragment(
      damage_pct=40,
      tones_per_fragment=4,
      pattern_key="castle-valley-a",
  )
```

With internal defaults like:

drop chance among damaged notes: 50%
duration chip chance if not dropped: 45%
amplitude chip chance if not dropped: 45%
duration keep range: 25%-80% of original duration
amplitude keep range: 10%-60% of original amplitude

`tones_per_fragment`=4

Meaning: when the transform creates a damaged patch, it tries to damage 4 adjacent notes at a time. The stochastic part is then limited to:

- where fragments start
- which final partial fragment is needed to hit damage_pct
- what kind of chip each selected note receives

Each fragment targets exactly tones_per_fragment adjacent original tones. If the remaining number of tones needed to satisfy damage_pct is smaller than
tones_per_fragment, the final fragment targets only that remaining number.

That gives the user a clearer mental model:

damage_pct = how much of the phrase is damaged
tones_per_fragment = how chunky the damage is
pattern_key = reuse this fragmentation pattern later

Example: 20 notes, damage_pct=40, tones_per_fragment=4 means 8 notes get damaged, likely as two 4-note damaged regions. That is much easier to predict than “up to 4
notes, maybe smaller, maybe scattered.”

### Proposed Design

- First sweep the original phrase with a random selector to pluck a random selection of notes in the phrase. The process should be stochastic and non-deterministic.
- After a randomly seleted sample is chosen, operate on the dimension to fragment or reduce it ("chip it away") as described in hte above block.
- optional pattern_key parameter to reuse the same figure, the same ruin later in the composition. If pattern_key is omitted, the transform is stochastic and non-deterministic.

# Fragment Transform Plan (Revised based on discussion)

## Summary

Add a phrase-level fragment transform that turns a phrase into a ruin-like sequence of missing and damaged tones. It preserves the original timeline while
stochastically choosing fragment start positions, creating silent holes, shortened remnants, and softened remnants.

## Key Changes

- Add a new phrase transform registered as fragment.
- Public params:
  - damage_pct: int: percentage of original tones to damage, 0-100.
  - tones_per_fragment: int: exact target width of each damaged patch, in adjacent tones.
  - pattern_key: string: optional; same pattern_key reproduces the same fragment pattern. If omitted, the transform is stochastic and non-deterministic.
  - Use a stable hash of pattern_key for repeatability. Do not use Python's built-in hash because it is randomized between processes.
- Selection behavior:
  - Compute the target damaged tone count from damage_pct using nearest whole tone, with nonzero percentages damaging at least one tone.
  - Randomly choose fragment start indexes.
  - Each full fragment damages exactly tones_per_fragment adjacent original tones; only the fragment may be smaller when needed to satisfy damage_pct.
  - Continue creating randomly placed fragments until the target damaged tone count is reached.
  - Choose from currently valid fragment starts rather than retrying indefinitely.
  - When no full-width start remains but damage count remains, create the final partial fragment from a valid remaining adjacent run.
- Damage behavior:
  - For each selected tone, roll full drop first.
  - Full drop replaces the tone with silence of the same duration.
  - If not dropped, independently roll duration shortening and amplitude softening.
  - If both non-drop rolls fail, force one non-drop chip so every selected tone is observably damaged.
  - Duration shortening emits a shortened tone plus trailing silence so total phrase duration is preserved.
  - Amplitude softening only reduces volume, never increases it.

  damage_pct determines the total number of tones to damage.
  tones_per_fragment determines the normal fragment size.
  If those two conflict, damage_pct wins for the final fragment.

  Example:
  - 20 tones, damage_pct=40, tones_per_fragment=4
  - Target damage count = 8 tones
  - Result = two full 4-tone fragments

  But:
  - 20 tones, damage_pct=30, tones_per_fragment=4
  - Target damage count = 6 tones
  - Result = one full 4-tone fragment + one final 2-tone fragment

  And:
  - 20 tones, damage_pct=10, tones_per_fragment=4
  - Target damage count = 2 tones
  - Result = one 2-tone fragment, because damaging 4 tones would violate damage_pct

- Suggested internal defaults:
  - Full drop chance: 50%.
  - Duration chip chance: 45%.
  - Amplitude chip chance: 45%.
  - Duration keep range: 25%-80%.
  - Amplitude keep range: 10%-60%.

## Test Plan

- Add unit tests for repeatable output with the same pattern_key.
- Verify different pattern_key values can choose different fragment start positions.
- Verify damage_pct controls how many original tones are selected for damage.
- Verify tones_per_fragment=4 creates damaged regions from randomly chosen starts and targets four adjacent tones per fragment.
- Verify dropped tones become silence with original duration.
- Verify shortened tones preserve timeline by adding trailing silence.
- Verify softened tones reduce amplitude and never increase it.
- Verify damage_pct=0 returns an equivalent phrase.
- Verify validation rejects negative percentages, percentages over 100, and tones_per_fragment < 1.
- Add registry/parser coverage so fragment works as a phrase transform.

## Assumptions

- V1 is phrase-level only, not score-level.
- The transform name is fragment.
- Silence is represented with Tone(frequency=0, amplitude=0.0, duration=...).
- Damaged fragment starts must be stochastic; pattern_key exists only to make a specific stochastic result reproducible.

## Implementation

- Use the iterative test-first plan in [fragment_transform_implementation_plan.md](./fragment_transform_implementation_plan.md).
- Start each step by adding failing observable-behavior tests, then implement the smallest production change needed to pass them.
