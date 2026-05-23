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
