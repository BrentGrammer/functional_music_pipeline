# Rename the generic _GenerateProfile Protocol

- This is a bad name. it is too generic and not expressive.

Target Naming:

```python
class _ToneDimensionFluctuationProfile(Protocol):
    def construct_fluctuations(self, how_many: int) -> list[float]: ...
```

## Considerations

- The signature does not match the spirit of the profile
- The fluctuation profile should construct fluctuations for some number of tones "how many"
- If the profile is just saying call this method to generate this number of fluctuations, maybe it should not be a profile and simply a callable definition?