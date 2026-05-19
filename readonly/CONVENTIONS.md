# AI Developer Conventions & Workflow

- Do not be verbose. Communicate the most important information in as concise a manner as possible.

When making changes to this codebase, please adhere to the following rules and conventions:

## 1. Testing Requirement

- Write tests that cover all new behavior added to the program.
- Do not tie tests too closely to implementation details. Tests should cover observable behavior, survive refactoring of the production code and not be brittle.

## 2. Iterative Development

- Make small, incremental changes as outlined in the `PROJECT_GOAL.md`.
- Ensure the pipeline architecture is respected (stateless transformations, separated I/O).

## 3. Comments

- Comments in the code should be avoided if possible. The code should be self-documenting and expressive so as to make the intent clear without needing a comment.
- In cases where the code might need explanation, then comments can be used, but they must explain the WHY and not the WHAT.
- Comments that only explain what the code is doing are redundant and not helpful unless what the code is doing is not intuitive.
- Commented documentation for functions is okay as long as the function is complicated enough to warrant it. Formats like Doc strings, JSDoc documentation is acceptable in these cases. Do not add documention for simple functions.

### Example of bad comments:

```python
for arg_name, func, takes_value in transform_specs:
    val = getattr(parsed_args, arg_name)
    if takes_value:
        # For value-taking flags, check if val is not None
        if val is not None:
            transforms_to_apply.append(lambda tones, f=func, v=val: f(tones, v))
    else:
        # For boolean flags, check if val is True
        if val:
            transforms_to_apply.append(func)
```

### Example of good comments that explain the WHY (don't actually write Why: in the comment, though):

```python
def test_mix_with_normalization(self):
    # 16-bit PCM audio has a strict maximum value of 32767.
    # If multiple playing tracks sum to a value higher than this, the integer overflows
    # and causes severe audio distortion (clipping). We must ensure the mixer prevents this.
    loud_track_1 = np.array([20000, -20000], dtype=np.int16)
    loud_track_2 = np.array([20000, -20000], dtype=np.int16)

    result = mix_waveforms([loud_track_1, loud_track_2])

    # The raw mathematical sum [40000, -40000] is too large.
    # The mixer must detect this and proportionally scale the entire array down
    # so the highest peak rests exactly at the safe 16-bit limit (32767).
    assert len(result) == 2
    assert result[0] == 32767
    assert result[1] == -32767
```

## 4. Magic Strings and Magic Numbers

- Where possible, magic strings and numbers should not be hard-coded, but be extracted to variables with descriptive and meaningful names that describes their purpose and meaning.
- The names of the variables should be all caps and in CAMEL_CASE.

## 5. Expressive Code

- Code should be expressive and self documenting.
- Write the code so you don't even need a lot of comments, since the names, variables and sequence it takes is telling an obvious story of what the intention and purpose of the code is.
- Names of variables and functions should be descriptive and express the intent and purpose.
- Do not use generic names like "data" or "stuff".
- Names of variables and functions should not lie. They should indicate clearly and honestly what they represent, what the variable's purpose is and what the function is doing.

## 6. Code Cleanliness

- Follow good software design principles such as those espoused by Martin Fowler, Kent Beck and Bob Martin.
- Code should be DRY (Do Not Repeat Yourself) where possible and practical. If you need to repeat the same behavior in code more than two or three times, then it should be abstracted into a shared module or function.
- Code should be easy to read and understand. It should not surprise you if you step through the code. The code should be so sensible that it is boring.
- Code should be separated in to modules that separate concerns to prevent too much coupling.
- Consider Domain Driven Design principles such has maintaining a business domain language that is consistent and maps to real-world objects relevant to the context.
- The code should be Easy To Change, debuggable and maintainable.
- Avoid introducing common and well-known code smells.

## 6b. Logging vs. Print

- Prefer using the standard Python `logging` module for all terminal output (INFO for success messages, WARNING/ERROR for issues).
- Avoid using `print()` for non-CLI usage/help text. This ensures the application remains modular and can be integrated into other systems or GUIs in the future without hijacking standard output.

#### 6a. Functions

- Functions should not have more than 4 parameters. A long list of parameters is a code smell and indicates the function is trying to do too much.
- Functions should have a low cyclomatic complexity. Do not write code that is more than 3 levels deep in nesting conditionals or similar constructs.
- Function names should be descriptive and clearly indicate what the function is doing. Prefer following the convention - verb_noun
  , ex: use `find_edge_nodes()` instead of `edge_nodes()`

##### Special Note on Helper Functions:

- DO NOT CREATE HELPER FUNCTIONS that do one tiny thing or are one liners. Unless the one line is complicated and hard to understand, these helpers do not add real value and just create indirection and noise.
- Example of bad helper function (it does one simple thing which is obvious and easy to understand if inlined and offers no value by wrapping the operation):

```python
def _phrase(name: str, *tones: Tone) -> Phrase:
    return Phrase(motifs=[Motif(name=name, tones=list(tones))])
```

## 7. Architecture and Design Principles

- When generating or refactoring code, you must adhere to the following architectural standards:

1. Prefer Composition over Inheritance. Code components should be composable.

2. **Design Pattern First-Thinking:** Before writing complex logic, evaluate if a Gang of Four (GoF) design pattern is applicable to ensure maintainability and scalability.
   - Use **Creational** patterns (e.g., Factory, Singleton, Builder) to manage object creation complexity.
   - Use **Structural** patterns (e.g., Adapter, Decorator, Facade) to handle relationships between entities and simplify interfaces.
   - Use **Behavioral** patterns (e.g., Strategy, Observer, Command, State) to eliminate heavy nested conditionals and decouple logic.

3. **SOLID Principles:**
   - **Single Responsibility:** Classes should have one reason to change.
   - **Open/Closed:** Code should be open for extension but closed for modification.
   - **Liskov Substitution:** Subtypes must be substitutable for their base types.
   - **Interface Segregation:** Prefer many small, specific interfaces over one large one.
   - **Dependency Inversion:** Depend on abstractions, not concretions.

4. **Refactoring Trigger:** If you find yourself writing deep `switch` statements or multiple `if/else` blocks based on object type or state, stop and refactor using the **Strategy** or **State** pattern instead.

5. **Functional Programming** Consider Functional Programming concepts if they would work well for the use case.
   - Functions should be pure and have no side effects.
   - Functions should be composable.

## 8. Structure and Organization

- Follow principles of Clean Architecture where applicable.
- Follow "Screaming Architecture": Top level file names and folder names should reflect the domain and purpose of the application instead of being tech stack specific.

## 9. Typing

- Where possible code should be staticly and strongly typed.
- If the programming language is not a strongly staticly typed langauge (like Python, for example), then type annotations must be used.
- Avoid redundant typing like typing a variable that is assigned to an already typed argument passed in.
- Always type annotate arguments and return types for functions.
- Prefer not using Any as a type annotation. If you must use Any, then explain why in a comment.
- Avoid manual type casting if possible. This indicates a possible code smell. If you need to type cast, then write a comment explaining why.
