# Parser Simplification Analysis

## The `resolve_profile_in_params` Code Smell

**Analysis:**
The `resolve_profile_in_params` function in `composition/parser.py` is a significant code smell for several reasons:
1. **Violates the Open/Closed Principle:** The parser explicitly hardcodes logic to intercept the parameter key `"profile"`. Adding new transforms that require complex objects (e.g., an `"envelope"`) would require modifying the parser again to handle those specific keys.
2. **Improper Coupling:** The parser's main responsibility is to map raw JSON strings/dicts to internal representations and orchestrate the pipeline. It should not need to know what a `StochasticProfile` is, nor should it depend on `build_profile`.
3. **Leaky Abstraction:** The parser is currently bridging the gap between raw JSON data and the domain object required by specific transforms (like `geological`), pulling domain-specific instantiation logic into the parsing layer.

**Recommendations:**
*   **Option A (Transform Handles It):** Update the specific transform functions (e.g., `apply_geological_transform`) to accept either a `dict` or a `StochasticProfile`. The parser passes the raw dictionary, and the transform calls `build_profile` internally. The parser remains ignorant of the profile.
*   **Option B (Deserializer in Spec):** Add an optional `deserializer` callback to the `TransformParamFieldSpec` dataclass in `transforms/base.py`. During parameter validation/processing, if a deserializer exists for a field, the raw JSON value is passed through it. This keeps the transform functions pure while keeping the parser generic.

## Other Helper Reductions

Further simplifications can be achieved by refactoring the other helper functions in `parser.py`:


