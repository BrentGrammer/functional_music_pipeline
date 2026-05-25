# Centralize Transform Param Validation

## Problem

The current transform params system splits validation across two places:

- `TransformParamFieldSpec` handles shape and type parsing.
- Individual transform modules often add separate validation functions for value rules such as numeric bounds.

This creates validation sprawl and weakens the purpose of the params spec abstraction. The `fragment` transform surfaced this clearly: the public params are declared in the spec, but range validation for `damage_pct` and `damage_tones_chunk_size` still lives in the transform module.

## Goal

Move transform param validation into the params spec layer so that:

- param definition and param validation live together
- transform modules do not need local param validation helpers for ordinary param rules
- the public transform API is easier to read and reason about
- validation behavior is more consistent across transforms

## Desired Direction

The params spec system should own:

- required vs optional fields
- type/schema parsing
- defaults
- value constraints such as min/max bounds
- any standard reusable validation rules that apply to a single field

Transform modules should only keep validation that is truly transform-specific and cannot be expressed cleanly at the params spec level, such as cross-field rules if those are later needed.

## Initial Plan

1. Extend the params system so field specs can express value constraints.
2. Prefer reusable schema or field-level validation instead of transform-local `_validate_*_params` functions.
3. Refactor existing transforms incrementally to move ordinary param validation into the spec layer.
4. Apply this direction to `fragment` before the transform grows more behavior.

## Candidate Approaches

Two reasonable approaches:

1. Add richer schema types such as bounded integer/float params.
2. Add validator support to `TransformParamFieldSpec` or `TransformParamsSpec` so parsed values can be checked in the spec layer.

The preferred direction is whichever keeps the API explicit, small, and easy to reuse across transforms.

## Current Assessment

The smallest useful version is probably:

1. Add bounded numeric schemas in `transforms/base.py`, such as a bounded integer param.
2. Add focused tests in `tests/test_transforms_base.py` for min/max validation and error behavior.
3. Update `fragment` to express `damage_pct` and `damage_tones_chunk_size` bounds through the params spec.
4. Remove ordinary range validation from `FragmentParams` construction if it is fully covered by the spec path.

Important caveat:

- `fragment_transform(...)` and `_select_chunks_to_damage(...)` are currently callable directly with raw integers.
- If local `_validate_fragment_params(...)` is removed entirely, direct callers can bypass spec validation.
- Before removing local validation, decide whether direct function calls should stay supported as public-ish APIs or whether callers should go through parsed `FragmentParams`.

Possible paths:

1. Keep direct-call guards in transform functions, but also add spec-level validation for registry/parser usage. This improves public param validation without fully eliminating duplication.
2. Move direct callers toward a params object or phrase-transform-only public API, then remove local range validation once the spec path owns all public entry points.
3. Add a shared reusable validation helper that both the spec layer and direct-call guards can use, reducing duplication without forcing a larger API migration.

Recommendation:

- Start with bounded integer schema support and tests.
- Apply it to `fragment` first.
- Do not remove all local `fragment` validation until the direct-call API boundary is clarified.
