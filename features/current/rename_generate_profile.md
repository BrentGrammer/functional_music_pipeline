# Rename the generic _GenerateProfile Protocol

- This is a bad name. it is too generic and not expressive.

Target Naming:

```python
class _ToneDimensionFluctuationProfile(Protocol):
    def construct_fluctuations(self, tone_count: int) -> list[float]: ...
```
