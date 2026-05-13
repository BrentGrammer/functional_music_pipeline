from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum, StrEnum, auto
from typing import Protocol, TypeAlias

from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice

ToneSequence: TypeAlias = list[Tone]
ScorePipelineStep: TypeAlias = Callable[[Score], Score]
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


class TransformParamType(Enum):
    FLOAT = auto()
    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    ENUM = auto()
    OBJECT = auto()


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
class ObjectParam(ParamSchema):
    fields: dict[str, "TransformParamFieldSpec"]
    allow_unknown_fields: bool = False

    def validate(self, value: object, field_name: str) -> None:
        if not isinstance(value, dict):
            raise ValueError(f"Param '{field_name}' must be an object/dictionary.")
        
        required_fields = tuple(k for k, v in self.fields.items() if v.required)

        if not self.allow_unknown_fields:
            unknown_fields = tuple(k for k in value if k not in self.fields)
            if unknown_fields:
                unknown_fields_description = ", ".join(f"'{f}'" for f in unknown_fields)
                raise ValueError(
                    f"Param '{field_name}' includes unknown fields: {unknown_fields_description}."
                )

        missing_fields = tuple(k for k in required_fields if k not in value)
        if missing_fields:
            missing_fields_description = ", ".join(f"'{f}'" for f in missing_fields)
            raise ValueError(
                f"Param '{field_name}' must include {missing_fields_description}."
            )

        for child_name, child_value in value.items():
            if child_name not in self.fields:
                continue
            child_spec = self.fields[child_name]
            if child_spec.schema is not None:
                schemas = child_spec.schema if isinstance(child_spec.schema, tuple) else (child_spec.schema,)
                errors = []
                is_valid = False
                for schema in schemas:
                    try:
                        schema.validate(child_value, f"{field_name}.{child_name}")
                        is_valid = True
                        break
                    except ValueError as e:
                        errors.append(str(e))
                        
                if not is_valid:
                    if len(errors) == 1:
                        raise ValueError(errors[0])
                    else:
                        raise ValueError(f"Param '{field_name}.{child_name}' failed validation: " + " OR ".join(errors))


@dataclass(frozen=True)
class TransformParamFieldSpec:
    param_type: TransformParamType | tuple[TransformParamType, ...] | None = None
    required: bool = False
    allowed_enum_values: tuple[object, ...] = ()
    schema: ParamSchema | tuple[ParamSchema, ...] | None = None


@dataclass(frozen=True)
class TransformParamsSpec:
    fields: dict[str, TransformParamFieldSpec] = field(default_factory=dict)
    validator: TransformParamsValidator | None = None


@dataclass(frozen=True)
class TransformDescriptor:
    name: str
    params_spec: TransformParamsSpec = field(default_factory=TransformParamsSpec, kw_only=True)

    def validate_params(self, transform_params: Mapping[str, object]) -> None:
        field_specs = self.params_spec.fields
        required_fields = tuple(field_name for field_name, field_spec in field_specs.items() if field_spec.required)

        unknown_fields = tuple(field_name for field_name in transform_params if field_name not in field_specs)
        if unknown_fields:
            unknown_fields_description = ", ".join(f"'{field}'" for field in unknown_fields)
            raise ValueError(
                f"The '{self.name}' transform params include unknown fields: {unknown_fields_description}."
            )

        missing_fields = tuple(field for field in required_fields if field not in transform_params)
        if missing_fields:
            missing_fields_description = ", ".join(f"'{field}'" for field in missing_fields)
            raise ValueError(
                f"The '{self.name}' transform params must include {missing_fields_description}."
            )

        for field_name, field_value in transform_params.items():
            field_spec = field_specs[field_name]
            
            if field_spec.schema is not None:
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
                    else:
                        raise ValueError(f"Param '{field_name}' failed validation: " + " OR ".join(errors))
            else:
                if not self._is_valid_transform_param_field(field_value, field_spec):
                    raise ValueError(
                        f"The '{self.name}' transform param '{field_name}' has an invalid type."
                    )

        if self.params_spec.validator is not None:
            self.params_spec.validator(transform_params)

    def _is_valid_transform_param_field(
        self,
        field_value: object,
        field_spec: TransformParamFieldSpec,
    ) -> bool:
        param_types = field_spec.param_type
        if not isinstance(param_types, tuple):
            param_types = (param_types,)

        return any(
            self._is_valid_transform_param_type(field_value, param_type, field_spec)
            for param_type in param_types
        )

    def _is_valid_transform_param_type(
        self,
        field_value: object,
        param_type: TransformParamType,
        field_spec: TransformParamFieldSpec,
    ) -> bool:
        match param_type:
            case TransformParamType.FLOAT:
                # Python treats bool as an int subclass, but JSON booleans are not numeric params.
                return isinstance(field_value, (float, int)) and not isinstance(field_value, bool)
            case TransformParamType.INTEGER:
                # Python treats bool as an int subclass, but JSON booleans are not numeric params.
                return isinstance(field_value, int) and not isinstance(field_value, bool)
            case TransformParamType.STRING:
                return isinstance(field_value, str)
            case TransformParamType.BOOLEAN:
                return isinstance(field_value, bool)
            case TransformParamType.ENUM:
                if isinstance(field_value, str):
                    return any(
                        isinstance(v, str) and v.lower() == field_value.lower()
                        for v in field_spec.allowed_enum_values
                    )
                return False
            case TransformParamType.OBJECT:
                return isinstance(field_value, dict) or hasattr(field_value, "__dict__")

        raise AssertionError(f"Unsupported transform param type: {param_type}")


@dataclass(frozen=True)
class PhraseTransform(TransformDescriptor):
    transform: Callable[..., ToneSequence]


@dataclass(frozen=True)
class PhraseRelativeTransform(TransformDescriptor):
    transform: Callable[..., ToneSequence]


@dataclass(frozen=True)
class ScoreTransform(TransformDescriptor):
    transform: Callable[..., Score]


@dataclass(frozen=True)
class ScoreTargetMotifsTransform(TransformDescriptor):
    transform: Callable[..., Score]


@dataclass(frozen=True)
class AllVoicesTransform(TransformDescriptor):
    transform: Callable[..., ToneSequence]


TransformWithCallable: TypeAlias = (
    PhraseTransform | PhraseRelativeTransform | ScoreTransform | ScoreTargetMotifsTransform | AllVoicesTransform
)


class Transform(Protocol):
    def __call__(self, tones: ToneSequence) -> ToneSequence: ...


class ScoreTransformProtocol(Protocol):
    def __call__(self, score: Score) -> Score: ...


def apply_to_voice(
    voice_index: int,
    transform_func: Callable[..., ToneSequence],
    *args: int | float,
    **kwargs: object,
) -> ScorePipelineStep:
    def wrapper(score: Score) -> Score:
        if 0 <= voice_index < len(score.voices):
            modified_tones = transform_func(score.voices[voice_index].tones, *args, **kwargs)
            score.voices[voice_index] = Voice(modified_tones)
        return score

    return wrapper


def apply_to_all_voices(
    transform_func: Callable[..., ToneSequence],
    *args: int | float,
    **kwargs: object,
) -> ScorePipelineStep:
    def wrapper(score: Score) -> Score:
        for i, voice in enumerate(score.voices):
            modified_tones = transform_func(voice.tones, *args, **kwargs)
            score.voices[i] = Voice(modified_tones)
        return score

    return wrapper
