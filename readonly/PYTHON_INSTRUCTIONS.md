# Instructions for using Python to code

## Type Safety and Casting

- Avoid `typing.cast` wherever possible. If you encounter a situation where mypy cannot infer a type from a registry or factory, refactor the registry to use **Generics** or encapsulate the behavior within a **Strategy** class that defines a consistent interface.
