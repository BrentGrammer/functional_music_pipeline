# Typed Transform Params Redesign

## Summary

Keep JSON parsing and TransformRequest.params as Mapping[str, object], because that is the untyped external boundary. Move the typed boundary one layer
later: transform definitions should validate and parse raw params once during preparation, then execute transforms with typed, immutable parameter
objects instead of raw mappings.

This keeps the registry as dispatch-only wiring and removes repeated ad hoc narrowing from transform execution paths.

## Key Changes

- Add typed param objects per transform family, using frozen dataclasses such as DelayParams(seconds: float), InvertParams(dimension: ToneDimension), and
  NoParams.
- Add parser functions near each transform module, such as parse_delay_params(params) -> DelayParams, that validate raw mappings and normalize values
  once.
- Introduce typed transform definition support in transforms/base.py:
  - generic phrase definitions bind PhraseTransformContext + ParamsT -> Phrase;
  - generic score definitions bind Score + ParamsT -> Score;
  - definitions expose a non-generic prepare(raw_params) method so registries can stay heterogeneous without cast or Any.
- Update composition/transformer.py so preparation does lookup -> validate/parse -> close over typed params. The prepared callable should no longer pass
  raw mappings into the execution function.
- Keep direct adapter wrappers temporarily for compatibility with existing tests and callers, but make them thin wrappers around the same parser + typed
  implementation.

## Migration Steps

- Start with one no-param transform and one parameterized transform:
  - reverse: proves NoParams and unused-param cleanup.
  - invert or delay: proves typed parsing and normalized params.
- Convert the rest in small batches by transform family:
  - basic transforms;
  - proportion transforms;
  - complexity/geological transforms;
  - counterpoint/tempo transforms.
- After all registry entries use typed definitions, decide whether to remove old raw adapter wrappers or keep them as stable compatibility APIs.

## Test Plan

- For each migrated batch, run focused tests for the touched transforms plus parser/transformer tests.
- Add base-level tests that prove:
  - raw params validate and parse into typed params;
  - unknown fields still fail;
  - missing required fields still fail;
  - prepared transforms close over typed params and execute without raw mapping access.
- Run uv run mypy . once the first typed-definition slice is complete, then again after each larger batch.

## Assumptions

- JSON input stays unchanged.
- TransformRequest.params stays raw because it represents parsed external data.
- Registry entries stay name-to-definition wiring and do not regain lambdas, casts, or narrowing helpers.
- We avoid cast, Any, and production assert.
- The typed boundary should live at transform preparation time, not inside registry.py.

TransformParamsSpec is directly related, and I would not remove it in the first version of this redesign.

The clean role split should be:

TransformParamsSpec
: Public/raw input contract. It answers: “What fields can JSON provide, which are required, and what broad shape must they have?”

Typed param object, for example DelayParams
: Internal executable contract. It answers: “After validation/parsing/defaulting, what exact Python values does this transform implementation receive?”

Parser function, for example parse_delay_params(params) -> DelayParams
: The bridge. It should use the same semantics as the spec, then normalize values into concrete types.

So the pipeline becomes:

JSON params
-> TransformRequest.params: Mapping[str, object]
-> TransformParamsSpec validation
-> parse\_\*\_params(...) returns typed params object
-> typed transform implementation runs without Mapping[str, object]

The important part: TransformParamsSpec remains useful for generic validation, docs/schema-style introspection, unknown-field rejection, and current JSON
parser tests. It just stops being the only thing standing between raw JSON-shaped data and typed transform code.

I’d treat TransformParamsSpec as the external contract and typed param dataclasses as the internal contract.
