  # Adapter Parameter Validation Cleanup

  ## Summary

  Use TransformParamsSpec as the public validation source of truth. Adapters should not repeat full schema validation. They should only recover typed
  values from already-validated Mapping[str, object] params so the raw transform APIs can be called cleanly.

  ## Key Changes

  - Add a small follow-up cleanup before batch three:
      - Remove user-facing duplicate validation from the new batch-two phrase adapters.
      - Replace it with minimal local extraction/narrowing only where Python typing requires it.
      - Keep the registry wired to named adapters; do not move logic back into registry.py.
  - Keep validation in raw transform functions when they are callable directly:
      - apply_terraced_drift_transform should reject bool for max_step_change_pct, since it currently accepts True/False accidentally through
        isinstance(bool, int).
      - Keep existing raw transform validation such as intensity lookup and dimension parsing, because raw transforms are tested and callable outside the
        registry pipeline.
  - Treat adapter extraction as an internal invariant:
      - The adapter assumes descriptor.validate_params(...) already ran in composition/parser.py or composition/transformer.py.
      - Avoid restating full schema rules in every adapter.
      - Use short private helpers only if needed to avoid repeating the same type-narrowing pattern in batch three.

  ## Test Plan

  - Re-run the batch-two focused tests:
      - uv run pytest tests/test_json_parser.py tests/test_transformation.py tests/test_geological_modulation.py
  - Add or adjust one raw-transform test for apply_terraced_drift_transform(..., max_step_change_pct=True) to confirm bool is rejected at the raw API
    boundary.
  - Run uv run mypy .; current known failures are unrelated remaining score-side registry lambdas:
      - score_feigenbaum_sequence(score, **params)
      - frost_effect(score, **params)

  ## Assumptions

  - TransformParamsSpec remains the canonical validation mechanism for JSON/config-driven transform params.
  - Adapters are internal execution adapters, not the primary public validation boundary.
  - Raw transform functions remain safe to call directly from tests and Python code.

