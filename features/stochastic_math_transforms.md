# Stochastic Mathematical Transforms

## Concept
Introduce aleatoric (chance-based) elements to the pipeline using fundamental mathematical constants. This bridges the gap between strict procedural generation and organic, unpredictable rhythm and duration scaling.

A new set of transforms (e.g., "random-math-tone", "random-math-phrase") will randomly select a constant from a predefined list and randomly choose an operation (grow/multiply or shrink/divide) to apply as a scaling factor to durations.

## Proposed Mathematical Constants
Leveraging `sympy` for high precision where applicable:

**Native SymPy Constants:**
*   **Golden Ratio** (`sympy.GoldenRatio`) ≈ 1.618
*   **Euler's Number** (`sympy.E`) ≈ 2.718
*   **Euler-Mascheroni Constant** (`sympy.EulerGamma`) ≈ 0.577
*   **Pi** (`sympy.pi`) ≈ 3.141
*   **Catalan's Constant** (`sympy.Catalan`) ≈ 0.915
*   **Apéry's Constant** (`sympy.Apery`) ≈ 1.202

**Derived/Hardcoded Constants:**
*   **Feigenbaum Constant (δ)** ≈ 4.669 (already in codebase)
*   **Silver Ratio** = $1 + \sqrt{2}$ ≈ 2.414
*   **Plastic Constant** ≈ 1.324 (real root of $x^3 - x - 1 = 0$)
*   **Fine-Structure Constant (α)** ≈ 0.00729 (or $1/137$)

## Implementation Challenges & Considerations

### 1. Extreme Values (The Fine-Structure Constant)
Because $\alpha$ is roughly $1/137$, a random choice to "grow" a 0.5s phrase by its inverse could result in a massive 68.5s duration, while shrinking it could result in an inaudible 3ms click. We must define bounds or formula variations (e.g., $1 + \alpha$) to ensure the output remains musically viable and doesn't trigger our 10-minute memory exhaustion safeguard.

### 2. Lookahead for "Succeeding" Phrases
Our current pipeline evaluates `--then` phrases Just-In-Time (left-to-right). Phrase 2 knows the duration of Phrase 1, but Phrase 1 cannot know the duration of Phrase 2. To scale a phrase relative to a *succeeding* phrase, we must refactor `main.py` to support "lookahead"—parsing and instantiating all phrases in a voice into memory *before* running their specific transforms.

### 3. Testing Randomness
Automated tests require predictability. When building these transforms, we will need to temporarily seed Python's `random` module (e.g., `random.seed(42)`) within the test blocks so they reliably pick the exact same constant and operation during assertions.

## Proposed Next Steps
1.  Add the new constants to the established central constants file utilizing SymPy.
2.  Build a simple "random-math-tone" transform to test the randomizer mechanics.
3.  Address the "lookahead" architectural shift in `main.py` to support true bidirectional relative scaling.
4.  Build the "random-math-phrase" transform.

## Next Transform To Build
*   **stochastic-tempo-curve / stochastic_tempo_curve**: A duration transform where a phrase speeds up or slows down overall, but individual tone-to-tone duration changes vary stochastically instead of following a strict linear ramp.
    *   Useful parameters to consider: `direction` (`accelerando` or `ritardando`), `curve`, `jitter`, `seed`, and `preserve_total_duration`.
    *   This should be the next implementation target because it has a clear musical behavior and can reuse the existing duration transform patterns without requiring lookahead.

## Near-Future Easy Candidates
*   **random-math-phrase / random_math_scale**: Randomly choose a safe mathematical constant and multiply or divide an entire phrase's duration. This is the easiest first implementation because it can reuse the existing scale transform pattern.
*   **score-random-math-scale**: Apply the same simple random constant scaling to all voices at score level, following the existing `score_scale` registration pattern.
*   **random-math-tone**: Randomly choose constants per tone for more jagged duration variation. Still feasible, but slightly less predictable musically than phrase-level scaling.
*   **constant-specific scale aliases**: Add direct transforms for simple constants such as silver ratio, plastic constant, pi, or Euler's number. These are straightforward once the constants are centralized.

Defer fine-structure constant behavior and succeeding-phrase lookahead until after the basic random math transforms are working.
