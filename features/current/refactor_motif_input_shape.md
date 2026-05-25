# refactor duration and frequency setting in motif

- The motif should have name, frequency and duration as a separate parameter, not a colon dilineated value.

Use this:

```json
{
    "motifs": {
        "motif-a": [{ "frequency": 440.0, "duration_seconds": 1.5 }, { "frequency": 520.0, "duration_seconds": 2.0 }, ...],
        "motif-b": [{ "frequency": 600.0, "duration_seconds": 0.5 }, { "frequency": 310.0, "duration_seconds": 4.0 }, ...]
    }
}
```

and do not use this current implementation (replace with above):

```json
{
    "motifs": {
        "motif-a": ["440.00:1.5", "520.0:2.0", ...],
        "motif-b": ["600.00:0.5", "310:4.0", ...]
    }
}
```
