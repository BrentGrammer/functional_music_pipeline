# Making Motifs in the JSON doc input optional

Users should optionally be able to provide a named list of motifs, but they can also directly inline motif strings (`frequency:duration`) into phrases. This allows the user to add adhoc motifs inline as well as reference named motifs in the composition.

The key distinction is:

- external JSON phrase input may contain either:
  - motif references
  - inline tone strings
- internal pipeline should still normalize both into motifs before the rest of the system uses them

So PhraseConfig as an internal trusted type should still contain motifs. The flexibility belongs at the boundary/parser input layer, not in the internal model.

That means the change is mostly a boundary parsing refactor:

1. Broaden the accepted phrase input shape at the boundary.
2. Validate which variant the user provided.
3. Normalize inline tone strings into generated/internal Motif objects or motif-like internal entries before the rest of the pipeline.
4. Keep downstream code working with motifs only.

So this does not invalidate the work we’ve done. In fact, it reinforces it:

- boundary accepts broader user input
- boundary validates and normalizes
- internal code stays strict and trusted

The main thing that will need adjustment is that the current phrase validation assumes "motifs" is present in the input document. If inline tones are allowed,
that assumption moves from:

- “phrase must have motifs”
  to
- “phrase must have exactly one valid musical source form, such as motifs or inline tones”

So the next design step is not a broad rewrite. It is to define the exact external phrase schema you want. For example:

- {"motifs": ["seed", "answer"]}
- or {"tones": ["440:1.0", "494:0.5"]}
