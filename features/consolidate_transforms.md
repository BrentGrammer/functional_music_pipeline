# Consolidate File Structure of Transform Modules

- The structure and organization of the Transforms modules is inconsistent and messy. Some transforms are grouped in a category file like "geological" and others are just flat files with only one transform in them.
- The organization should be cleaned up to be less haphazard
  - Cellular Automata does not belong with Geological Transforms
  - Erosion transform should be with other Geological Transforms if we're grouping them together.


### Proposed Organization of Transforms

transforms/
    base.py
    registry.py

    simple/
        reversal.py
        inversion.py
        transpose.py
        scale.py
        repeat.py
        delay.py
        pad_silence.py
        drift.py

    tempo/
        accelerando.py
        ritardando.py

    proportion/
        feigenbaum.py
        golden_ratio.py

    counterpoint/
        fugue.py           # stretto + add_pedal_point

    geological/
        drops.py           # random_drop + ridged_drop
        terraced_drift.py
        weierstrass.py
        erosion.py
        frost_effect.py

    generative/
        cellular_automata.py