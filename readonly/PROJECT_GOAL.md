# Project Goal: Algorithmic Tone Transformer

## Core Objective

To develop a system that accepts short melodic motifs, applies algorithmic transformations (inversion, retrograde, etc.), and outputs the result as a WAV file.
The primary purpose of this project is to experiment with ideas coming from the realm of Chaos Theory, the Complex Sciences and Stephen Wolfram's idea of Computational Irreducibility and how they can be applied to composing music.
One of the main ideas that inspired this project is the curiosity about how you can construct music which is computationally irreducible and complex in the sense that it is the unpredictable and relatively complex outcome of following simple rules and iterating on them to produce the final and surprising result.
The music produced by this program should be the emergent property of the algorithms and their various combinations whose application is left up to the user to decide and experiment with.

## Technical North Stars

- **Stateless Transformations:** Algorithms should be modular and treat motifs as data.
- **Polyphonic Support:** While starting monophonic, the architecture must support concurrent waveforms so as to produce polyphonic results.
- **Audio Backend:** Currently using `pyaudio`, but open to abstractions that simplify polyphony (e.g., `numpy` for wave summing).
- **Usability & UI:** Progressively make the tool easier to use for composition (e.g., supporting motifs and aliases). Long-term, the project aims to evolve toward a Graphical User Interface (UI) for more visual and intuitive manipulation.

## Implementation Pace

- The goal should be reached by implementing features in an interative way.
- Short iterations and small changes should be prioritized to slowly and iteratively reach the end goal of the program.

## Summary

- To summarize, the eventual end goal is to:

1.  Accept a series of tones or melodies.
2.  Run algorithms that transform these tones. The user could apply multiple transoforms and they are piped into each other so that a new transform modifies the output of the last transform.
3.  Produce a .wav file of the transformed result.
4.  Ideally, support polyphonic capability for multiple tones at the same time.
5.  Long-term, provide a UI to streamline the creative process of combining and transforming tone sequences.

## Domain Models

- Motif: A sequence of tones
- Phrase: One or more motifs
- Voice: A phrase or group of phrases that can be polyphonically played at the same time as another Voice
- Score: One or more Voices

### Heirarchy of the Domain Objects

- Motifs build Phrases
- Phrases build Voices
- Voices build Scores

## Design/Architecture

- The main idea is to create a functional programming style pipeline to send musical ideas to.
- The main components are meant to be composable. From top to bottom the heirarchy is: Composition > Voices > Phrases > Motifs
- Motifs are basic building blocks and used to build Phrases. 
- Phrases are used to build Voices. A composition can have one or more Voices.
- Phrases are monophonic lines while Voices can be polyphonic and played at the same time.


