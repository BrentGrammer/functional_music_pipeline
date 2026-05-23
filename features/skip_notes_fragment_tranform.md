# Fragment Transform

- A transform that turns a melody or phrase into a fragment with randomly missing notes or pieces.
- Similar to an ancient Ruin which once was whole, but now is missing pieces and fragmented.
- Reminiscent of broken, jagged fragmented rock formations such as those in Castle Valley in Utah.

## Desired Behavior

- A Phrase has random parts of it removed:
  - Frequency
    - random tones are removed replacing them with silence
  - Duration
    - the duration of notes is randomly shortened to various degrees
    - By how much?
    - Every note or pick random selection? Probably initial sweep to select random notes, then apply the fragmentation to the dimension on those randomly selected notes from the phrase.
  - Amplitude
    - Random selected tones have their amplitude drastically reduced and modified to be softer. (always taking away, so we don't increase)

### Proposed Design

- First sweep the original phrase with a random selector to pluck a random selection of notes in the phrase. The process should be stochastic and non-deterministic.
- After a randomly seleted sample is chosen, operate on the dimension to fragment or reduce it ("chip it away") as described in hte above block.
