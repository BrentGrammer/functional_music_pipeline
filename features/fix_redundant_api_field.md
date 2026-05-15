# Fix Redundant API Field

- The public API currently has two fields named "motifs"
- Consider not using the same field name twice?

```json
{
  "motifs": {
    "seed_a": ["155.56:0.3", "185.00:0.15"],
    "seed_b": ["622.25:0.2", "440:0.25"]
  },
  "composition": {
    "voices": [
      {
        "phrases": [
          {
            "line": ["seed_a", "seed_b"],
            "transforms": [
              {
                "name": "reverse"
              }
            ]
          }
        ]
      }
    ]
  }
}
```
