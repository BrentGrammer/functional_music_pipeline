# Consolidate File Structure of Transform Modules

The current transform package is organized inconsistently. Some transforms live in
single-transform files, while the current `geological.py` file mixes unrelated
concepts such as cellular automata with geological-style transforms.

The cleanup should organize transforms by primary conceptual identity, not by
one file per transform and not by implementation traits like "stochastic." This
keeps related helpers together, makes the registry easier to read, and avoids
categories that overlap with each other.

## Proposed Organization

```text
transforms/
    base.py
    registry.py

    basic/
        reversal.py
        inversion.py
        transpose.py
        scale.py
        repeat.py
        delay.py
        pad_silence.py
        drift.py

    tempo/
        curves.py          # accelerando + ritardando

    proportion/
        golden_ratio.py
        feigenbaum.py

    counterpoint/
        fugue.py           # stretto + add_pedal_point

    complexity/
        weierstrass.py
        cellular_automata.py
        random_drop.py

    geological/
        erosion.py
        frost_effect.py
        terraced_drift.py
        ridged_drop.py
```

## Key Decisions

- Keep public transform names stable in JSON and in `TRANSFORMS`.
- Use `complexity` for transforms rooted in complex systems, fractals, chaos,
  cellular automata, nonlinear patterns, or computational irreducibility.
- Move cellular automata into `complexity` because it is a formal complex-systems
  process, not a geological transform.
- Move Weierstrass and random drop into `complexity` because their primary
  identity is generated complexity rather than a geological metaphor.
- Keep terraced drift and ridged drop under `geological` because their public
  concepts are geological surface forms.
- Do not keep a separate `profiles.py` module. The profile generators should be
  private helpers in the transform modules that use them, so each transform
  module follows the existing pattern of keeping params, transform functions,
  and supporting implementation together.
- Keep erosion and frost effect under `geological` because those are explicitly
  geological/metaphor-driven effects.
- Do not use `stochastic` as a folder name. Randomness is an implementation
  trait that can appear in multiple conceptual categories.
- Do not preserve old direct Python import paths such as
  `transforms.geological.apply_stochastic_profile`; update tests and internal
  imports to the new locations.

## Implementation Notes

- `transforms/registry.py` remains the public transform registry and should only
  need import-path updates.
- Profile classes and generated-pattern helpers should become private
  implementation details inside the relevant transform modules, not public
  imports.
- Composition files should not change.
- Transform parameter specs, defaults, and behavior should remain unchanged.
- Tests should be updated to import from the new modules and then the full
  `pytest` suite should pass.
