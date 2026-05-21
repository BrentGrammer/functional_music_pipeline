# Rename the generic \_GenerateProfile Protocol

- This is a bad name. it is too generic and not expressive.
- Also, we need to consider whether to drop this approach totally.
  - There is too much indirection and coupling.
  - The Profile in modulation module does not know about the profile in terraced_drift which uses `generate` and vice versa. This is poor design.
  - There probably is a simpler way to refactor the transforms that use the _GenerateProfile or Profiles.
Target Naming:

```python
class _ToneDimensionFluctuationProfile(Protocol):
    def construct_fluctuations(self, how_many: int) -> list[float]: ...
```

## Considerations

- The signature does not match the spirit of the profile
- The fluctuation profile should construct fluctuations for some number of tones "how many"
- If the profile is just saying call this method to generate this number of fluctuations, maybe it should not be a profile and simply a callable definition?

## Revised plan - simpler

then a plain callable may be cleaner.

Something like:

```python
from collections.abc import Callable

FluctuationBuilder = Callable[[int], list[float]]
```

Then:

```python
def apply_fluctuation_profile(
    tones: ToneSequence,
    build_fluctuations: FluctuationBuilder,
    dimension: ToneDimension | str,
    max_deviation: float,
) -> ToneSequence:
    ...
    fluctuations = build_fluctuations(len(tones))
```

Usage:

```python
profile = _RandomDropFluctuationProfile(seed=42, drop_rate=drop_rate)

return apply_fluctuation_profile(
    tones,
    profile.build_fluctuations,
    dimension,
    max_deviation,
)
```

That may actually clarify the design:

\_RandomDropFluctuationProfile can still exist as a config object.
But the shared modulation function only needs a fluctuation-building function.
The protocol may be unnecessary unless you want to standardize profile objects.

Possible type names:

```
FluctuationBuilder
FluctuationFactory
FluctuationGenerator
```

My pick:

```python
FluctuationBuilder = Callable[[int], list[float]]
```

because it pairs nicely with:

```python
build_fluctuations(how_many)
```

So yes: if all you need is “give me N fluctuations,” passing a callable is arguably simpler and more honest than a profile protocol.
