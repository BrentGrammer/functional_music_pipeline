from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, StrEnum, auto
from typing import Protocol, TypeAlias

from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice

ToneSequence: TypeAlias = list[Tone]
ScorePipelineStep: TypeAlias = Callable[[Score], Score]
TransformParamsValidator: TypeAlias = Callable[[dict[str, object]], None]


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


@dataclass(frozen=True)
class TransformParamFieldSpec:
    param_type: TransformParamType | tuple[TransformParamType, ...]
    required: bool = False
    allowed_enum_values: tuple[object, ...] = ()


@dataclass(frozen=True)
class TransformParamsSpec:
    fields: dict[str, TransformParamFieldSpec] = field(default_factory=dict)
    validator: TransformParamsValidator | None = None


@dataclass(frozen=True)
class TransformDescriptor:
    name: str
    params_spec: TransformParamsSpec = field(default_factory=TransformParamsSpec)


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


class Transform(Protocol):
    def __call__(self, tones: ToneSequence) -> ToneSequence: ...


class ScoreTransformProtocol(Protocol):
    def __call__(self, score: Score) -> Score: ...


def apply_to_voice(
    voice_index: int,
    transform_func: Callable[..., ToneSequence],
    *args: int | float,
    **kwargs: int | float | str | bool,
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
    **kwargs: int | float | str | bool,
) -> ScorePipelineStep:
    def wrapper(score: Score) -> Score:
        for i, voice in enumerate(score.voices):
            modified_tones = transform_func(voice.tones, *args, **kwargs)
            score.voices[i] = Voice(modified_tones)
        return score

    return wrapper
