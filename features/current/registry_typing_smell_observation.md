# Feature Note: Registry Typing Smell Observation

## Context

During the mypy cleanup for the transform registry, we ended up adding several tiny parameter-narrowing helpers to convert `Mapping[str, object]` values into the concrete types expected by individual transform functions.

That felt wrong.

## Observation

The helpers are not the real problem. They are a symptom of a deeper design mismatch:

- The registry is doing dispatch.
- The registry is also doing parameter recovery and type narrowing.
- The registry is adapting untyped JSON-shaped params into many different typed transform APIs.

That means one generic layer is trying to represent a family of distinct call signatures.

## Smell

The smell is a leaky abstraction:

- transform definitions have real, specific parameter shapes,
- but the registry only sees `Mapping[str, object]`,
- so every call site has to re-derive the concrete types manually.

That produces helper churn, repeated narrowing logic, and a strong hint that the type model does not match the design.

## Why This Matters

This is not just a typing inconvenience.
It suggests the architecture is pushing too much responsibility into the registry layer.

If the design were healthier, we would not need to keep adding tiny helpers just to make mypy accept code that is already "obviously" valid at runtime.

## Working Hypothesis

The real fix likely involves reducing registry responsibility and making the typed shape of each transform clearer at the boundary where JSON params become executable transform inputs.

Possible directions to explore later:

- move adaptation closer to each transform module,
- introduce typed parameter objects instead of raw `Mapping[str, object]`,
- separate dispatch from adaptation more cleanly.

## Status

This note is intentionally not a solution plan.
It records the smell so we can recognize the underlying problem before deciding how to redesign it.