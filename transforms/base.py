from collections.abc import Callable, Mapping
from dataclasses import MISSING, dataclass, field
from enum import StrEnum, auto
from typing import Generic, Protocol, TypeAlias, TypeVar

from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone

ToneSequence: TypeAlias = list[Tone]
ParsedParam = TypeVar("ParsedParam")
ParsedParams = TypeVar("ParsedParams")


class ToneDimension(StrEnum):
    FREQUENCY = auto()
    DURATION = auto()
    AMPLITUDE = auto()


class ParamSchema(Generic[ParsedParam]):
    """Base class for all parameter shapes/types."""

    def parse(self, value: object, field_name: str) -> ParsedParam:
        raise NotImplementedError

    def validate(self, value: object, field_name: str) -> None:
        self.parse(value, field_name)


@dataclass(frozen=True)
class FloatParam(ParamSchema[float]):
    def parse(self, value: object, field_name: str) -> float:
        if not isinstance(value, (float, int)) or isinstance(value, bool):
            raise ValueError(f"Param '{field_name}' must be a float.")
        return float(value)


@dataclass(frozen=True)
class IntegerParam(ParamSchema[int]):
    def parse(self, value: object, field_name: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Param '{field_name}' must be an integer.")
        return value


@dataclass(frozen=True)
class StringParam(ParamSchema[str]):
    def parse(self, value: object, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"Param '{field_name}' must be a string.")
        return value


@dataclass(frozen=True)
class BooleanParam(ParamSchema[bool]):
    def parse(self, value: object, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"Param '{field_name}' must be a boolean.")
        return value


@dataclass(frozen=True)
class ToneDimensionParam(ParamSchema[ToneDimension]):
    def parse(self, value: object, field_name: str) -> ToneDimension:
        if not isinstance(value, ToneDimension):
            raise ValueError(f"Param '{field_name}' must be a ToneDimension.")
        return value


@dataclass(frozen=True)
class EnumParam(ParamSchema[str]):
    allowed_values: tuple[str, ...]

    def parse(self, value: object, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"Param '{field_name}' must be one of {self.allowed_values}.")
        normalized_value = value.lower()
        normalized_allowed_values = {allowed_value.lower(): allowed_value.lower() for allowed_value in self.allowed_values}
        if normalized_value not in normalized_allowed_values:
            raise ValueError(f"Param '{field_name}' must be one of {self.allowed_values}.")
        return normalized_allowed_values[normalized_value]


@dataclass(frozen=True)
class NoParams:
    pass


@dataclass(frozen=True)
class TransformParamFieldSpec:
    schema: ParamSchema | tuple[ParamSchema, ...]
    required: bool = False
    # MISSING lets parse-time code distinguish "no default declared" from an explicit default like None.
    default: object = field(default_factory=lambda: MISSING)


@dataclass(frozen=True)
class ParsedTransformParams:
    values: Mapping[str, object]

    def required(self, field_name: str, expected_type: type[ParsedParam]) -> ParsedParam:
        value = self.values[field_name]
        if not isinstance(value, expected_type):
            raise TypeError(f"Parsed transform param '{field_name}' violated its schema contract.")
        return value


@dataclass(frozen=True)
class TransformParamsSpec(Generic[ParsedParams]):
    params_factory: Callable[[ParsedTransformParams], ParsedParams]
    fields: dict[str, TransformParamFieldSpec] = field(default_factory=dict)

    def parse_params(
        self,
        raw_params: Mapping[str, object],
        transform_name: str | None = None,
    ) -> ParsedParams:
        transform_description = f"The '{transform_name}' transform params" if transform_name is not None else "Transform params"

        unknown_fields = tuple(field_name for field_name in raw_params if field_name not in self.fields)
        if unknown_fields:
            unknown_fields_description = ", ".join(f"'{field}'" for field in unknown_fields)
            raise ValueError(f"{transform_description} include unknown fields: {unknown_fields_description}.")

        missing_fields = tuple(
            field_name for field_name, field_spec in self.fields.items() if field_spec.required and field_name not in raw_params and field_spec.default is MISSING
        )
        if missing_fields:
            missing_fields_description = ", ".join(f"'{field}'" for field in missing_fields)
            raise ValueError(f"{transform_description} must include {missing_fields_description}.")

        parsed_params: dict[str, object] = {}
        for field_name, field_spec in self.fields.items():
            if field_name in raw_params:
                parsed_params[field_name] = _parse_transform_param_value(
                    field_name=field_name,
                    field_value=raw_params[field_name],
                    field_spec=field_spec,
                )
                continue

            if field_spec.default is not MISSING:
                parsed_params[field_name] = field_spec.default

        parsed_params_model = self.params_factory(ParsedTransformParams(parsed_params))

        return parsed_params_model


def _parse_transform_param_value(
    field_name: str,
    field_value: object,
    field_spec: TransformParamFieldSpec,
) -> object:
    """
    Parse one transform param against its declared schema.

    Most fields use a single schema. Tuple schemas are a small escape hatch for
    fields that intentionally accept more than one input shape, such as a named
    preset or a numeric value.
    """
    field_schemas = field_spec.schema if isinstance(field_spec.schema, tuple) else (field_spec.schema,)
    if len(field_schemas) == 1:
        return field_schemas[0].parse(field_value, field_name)

    errors = []
    for candidate_schema in field_schemas:
        try:
            return candidate_schema.parse(field_value, field_name)
        except ValueError as e:
            errors.append(str(e))

    raise ValueError(f"Param '{field_name}' failed validation: " + " OR ".join(errors))


@dataclass(frozen=True)
class PhraseTransformContext:
    score: Score
    voice_index: int
    phrase_index: int

    @property
    def phrase(self) -> Phrase:
        return self.score.voices[self.voice_index].phrases[self.phrase_index]


@dataclass(frozen=True)
class PhraseTransformDefinition(Generic[ParsedParams]):
    name: str
    params_spec: TransformParamsSpec[ParsedParams]
    transform_function: Callable[[PhraseTransformContext, ParsedParams], Phrase]

    def transform(self, context: PhraseTransformContext, raw_params: Mapping[str, object]) -> Phrase:
        params = self.params_spec.parse_params(raw_params, transform_name=self.name)
        return self.transform_function(context, params)


@dataclass(frozen=True)
class ScoreTransformDefinition(Generic[ParsedParams]):
    name: str
    params_spec: TransformParamsSpec[ParsedParams]
    transform_function: Callable[[Score, ParsedParams], Score]

    def transform(self, score: Score, raw_params: Mapping[str, object]) -> Score:
        params = self.params_spec.parse_params(raw_params, transform_name=self.name)
        return self.transform_function(score, params)


class RegisteredPhraseTransform(Protocol):
    @property
    def name(self) -> str: ...

    def transform(self, context: PhraseTransformContext, raw_params: Mapping[str, object]) -> Phrase: ...


class RegisteredScoreTransform(Protocol):
    @property
    def name(self) -> str: ...

    def transform(self, score: Score, raw_params: Mapping[str, object]) -> Score: ...
