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

## Step-by-Step Implementation Plan

1. Create the new transform package directories with `__init__.py` files:
   `basic`, `tempo`, `proportion`, `counterpoint`, `complexity`, and
   `geological`.

2. Move the basic phrase transforms into `transforms/basic/` without behavior
   changes: `reversal`, `inversion`, `transpose`, `scale`, `repeat`, `delay`,
   `pad_silence`, and `drift`.

3. Update imports for the basic move, including `transforms/registry.py`, tests
   for those transforms, and internal imports such as references to `scale` or
   `delay`.

4. Run the targeted basic-transform tests if the environment supports it:
   `test_reversal`, `test_invert`, `test_transpose`, `test_scale`,
   `test_repeat`, `test_delay`, `test_pad_silence`, and `test_drift`.

5. Split `duration.py` into conceptual modules by moving `accelerando`,
   `ritardando`, and their tempo helper functions into
   `transforms/tempo/curves.py`.

6. Move Feigenbaum proportional transforms into
   `transforms/proportion/feigenbaum.py`, including `feigenbaum_sequence`,
   phrase Feigenbaum transforms, and `score_feigenbaum_sequence`.

7. Move golden ratio proportional transforms into
   `transforms/proportion/golden_ratio.py`.

8. Update tempo and proportion imports in the registry, tests, and any
   cross-module references.

9. Run targeted tempo and proportion tests if available: `test_duration`,
   `test_tempo_resolvers`, `test_feigenbaum_simple`, `test_golden_ratio`, and
   parser tests that reference `accelerando`, `ritardando`, `feigenbaum`, or
   `golden_ratio`.

10. Move counterpoint transforms by moving `fugue.py` to
    `transforms/counterpoint/fugue.py`, keeping `stretto` and
    `add_pedal_point` unchanged.

11. Update counterpoint imports and run `test_fugue` plus parser tests that
    reference `stretto` or `add_pedal_point`, if the environment supports test
    execution.

12. Create the complexity transform modules:
    `transforms/complexity/weierstrass.py`,
    `transforms/complexity/cellular_automata.py`, and
    `transforms/complexity/random_drop.py`.

13. Move each complexity transform's params spec, public transform function, and
    private generator/profile helpers into its module:
    `WEIERSTRASS_PARAMS_SPEC` with `apply_weierstrass_transform`,
    `CELLULAR_AUTOMATA_PARAMS_SPEC` with `apply_cellular_automata_transform`,
    and `RANDOM_DROP_PARAMS_SPEC` with `apply_random_drop_transform`.

14. Add a private shared modulation helper only if needed to avoid noisy
    duplication. If added, keep it private to the category, such as
    `transforms/complexity/_modulation.py`; do not create a public
    `profiles.py`.

15. Move geological transforms by moving `erosion.py` and `frost_effect.py` into
    `transforms/geological/`, then create `terraced_drift.py` and
    `ridged_drop.py`.

16. Move geological profile-backed transforms into their modules:
    `TERRACED_DRIFT_PARAMS_SPEC` with `apply_terraced_drift_transform`, and
    `RIDGED_DROP_PARAMS_SPEC` with `apply_ridged_drop_transform`, including
    private generator helpers beside each transform.

17. Delete the old public implementation modules after imports are updated:
    top-level `transforms/geological.py`, `transforms/profiles.py`,
    `transforms/duration.py`, and the moved top-level transform files.

18. Update `transforms/registry.py` so every registry key stays unchanged but
    imports from the new module paths.

19. Rewrite profile-focused tests around public transform behavior. Replace
    direct `transforms.profiles` tests with tests for deterministic output,
    empty input behavior, dimension modulation, and seeded repeatability through
    the public complexity and geological transform functions.

20. Update any remaining tests that import old paths. Tests should import from
    the new module paths directly; do not add compatibility shims for old direct
    Python imports.

21. Run broad validation if possible: the full `pytest` suite, then fix import
    errors, registry failures, and behavior regressions without changing
    transform names or params.

22. Optionally update example wording that says "stochastic profile transforms"
    if it now reads misleadingly. Do not change composition schema, transform
    names, or composition file behavior.

## Testing Caveat

- You do not need to run the tests after each change. I will run them manually and let you know if they pass or fail.
- Composition files should not change.
- Transform parameter specs, defaults, and behavior should remain unchanged.
