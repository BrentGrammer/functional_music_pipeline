from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol, TypeAlias

from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice

ToneSequence: TypeAlias = list[Tone]
ScorePipelineStep: TypeAlias = Callable[[Score], Score]
TransformParamsValidator: TypeAlias = Callable[[dict[str, object]], None]


class ToneDimension(Enum):
    FREQUENCY = auto()
    DURATION = auto()
    AMPLITUDE = auto()


def parse_dimension(dim: ToneDimension | str) -> ToneDimension:
    if isinstance(dim, ToneDimension):
        return dim
    try:
        return ToneDimension[str(dim).upper()]
    except KeyError:
        raise ValueError(f"Invalid dimension: {dim}. Must be one of {', '.join(d.name for d in ToneDimension)}")


class TransformScope(Enum):
    PHRASE = auto()
    PHRASE_RELATIVE = auto()
    SCORE = auto()
    SCORE_TARGET_MOTIFS = auto()
    ALL_VOICES = auto()


class TransformParamType(Enum):
    NUMBER = auto()
    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    ENUM = auto()
    OBJECT = auto()


@dataclass(frozen=True)
class TransformParamFieldSpec:
    param_type: TransformParamType
    required: bool = False
    allowed_values: tuple[object, ...] = ()


@dataclass(frozen=True)
class TransformParamsSpec:
    fields: dict[str, TransformParamFieldSpec] = field(default_factory=dict)
    validator: TransformParamsValidator | None = None

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(field_name for field_name, field_spec in self.fields.items() if field_spec.required)


@dataclass(frozen=True)
class TransformDescriptor:
    name: str
    scope: TransformScope
    transform: Callable
    params_spec: TransformParamsSpec = TransformParamsSpec()


class Transform(Protocol):
    def __call__(self, tones: ToneSequence) -> ToneSequence: ...


class ScoreTransform(Protocol):
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
