Best practice for a clean codebase is:

1. Public boundary functions accept object (or broad input) when they parse external/untrusted data.
2. Validate immediately at that boundary.
3. Then convert/narrow to strong internal types (TypedDict/dataclasses) for the rest of the pipeline.
4. Keep strict typed signatures for internal functions that assume valid data.

Why:

- External JSON is untyped at runtime.
- If boundary functions are strictly typed, tests for invalid input become awkward/noisy.
- You still get strong typing internally, where it provides the most value.

For your case:

- generate_score_plan(...) should be boundary-style (accept broad input + validate).
- Internal helpers after validation can use CompositionDocument, VoiceConfig, PhraseConfig, etc.
- This keeps runtime validation honest and mypy clean without massive test churn.
