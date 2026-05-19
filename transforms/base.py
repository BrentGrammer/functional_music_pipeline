from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TypeAlias

from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone

ToneSequence: TypeAlias = list[Tone]
TransformParamsValidator: TypeAlias = Callable[[Mapping[str, object]], None]


class ToneDimension(StrEnum):
    FREQUENCY = auto()
    DURATION = auto()
    AMPLITUDE = auto()


def parse_dimension(dim: ToneDimension | str) -> ToneDimension:
    if isinstance(dim, ToneDimension):
        return dim
    try:
        return ToneDimension(str(dim).lower())
    except ValueError:
        raise ValueError(f"Invalid dimension: {dim}. Must be one of {', '.join(d.value for d in ToneDimension)}")


class ParamSchema:
    """Base class for all parameter shapes/types."""
    def validate(self, value: object, field_name: str) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class FloatParam(ParamSchema):
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise ValueError(f"Param '{field_name}' must be a float.")


@dataclass(frozen=True)
class IntegerParam(ParamSchema):
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Param '{field_name}' must be an integer.")


@dataclass(frozen=True)
class StringParam(ParamSchema):
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, str):
            raise ValueError(f"Param '{field_name}' must be a string.")


@dataclass(frozen=True)
class BooleanParam(ParamSchema):
    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, bool):
            raise ValueError(f"Param '{field_name}' must be a boolean.")


@dataclass(frozen=True)
class EnumParam(ParamSchema):
    allowed_values: tuple[str, ...]

    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, str) or value.lower() not in (v.lower() for v in self.allowed_values):
            raise ValueError(f"Param '{field_name}' must be one of {self.allowed_values}.")


@dataclass(frozen=True)
class TransformParamFieldSpec:
    schema: ParamSchema | tuple[ParamSchema, ...]
    required: bool = False


@dataclass(frozen=True)
class TransformParamsSpec:
    fields: dict[str, TransformParamFieldSpec] = field(default_factory=dict)
    validator: TransformParamsValidator | None = None


def validate_transform_params(
    params_spec: TransformParamsSpec,
    name: str,
    params: Mapping[str, object],
) -> None:
    field_specs = params_spec.fields
    required_fields = tuple(field_name for field_name, field_spec in field_specs.items() if field_spec.required)

    unknown_fields = tuple(field_name for field_name in params if field_name not in field_specs)
    if unknown_fields:
        unknown_fields_description = ", ".join(f"'{field}'" for field in unknown_fields)
        raise ValueError(f"The '{name}' transform params include unknown fields: {unknown_fields_description}.")

    missing_fields = tuple(field for field in required_fields if field not in params)
    if missing_fields:
        missing_fields_description = ", ".join(f"'{field}'" for field in missing_fields)
        raise ValueError(f"The '{name}' transform params must include {missing_fields_description}.")

    for field_name, field_value in params.items():
        field_spec = field_specs[field_name]

        schemas = field_spec.schema if isinstance(field_spec.schema, tuple) else (field_spec.schema,)
        errors = []
        is_valid = False
        for schema in schemas:
            try:
                schema.validate(field_value, field_name)
                is_valid = True
                break
            except ValueError as e:
                errors.append(str(e))

        if not is_valid:
            if len(errors) == 1:
                raise ValueError(errors[0])
            raise ValueError(f"Param '{field_name}' failed validation: " + " OR ".join(errors))

    if params_spec.validator is not None:
        params_spec.validator(params)


@dataclass(frozen=True)
class PhraseTransformContext:
    score: Score
    voice_index: int
    phrase_index: int

    @property
    def phrase(self) -> Phrase:
        return self.score.voices[self.voice_index].phrases[self.phrase_index]


@dataclass(frozen=True)
class PhraseTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    transform: Callable[[PhraseTransformContext, Mapping[str, object]], Phrase]

    def validate_params(self, params: Mapping[str, object]) -> None:
        validate_transform_params(self.params_spec, self.name, params)


@dataclass(frozen=True)
class ScoreTransformDefinition:
    name: str
    params_spec: TransformParamsSpec
    transform: Callable[[Score, Mapping[str, object]], Score]

    def validate_params(self, params: Mapping[str, object]) -> None:
        validate_transform_params(self.params_spec, self.name, params)
