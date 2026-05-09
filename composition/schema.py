from typing import TypedDict, NotRequired, TypeAlias


PrimitiveParamValue: TypeAlias = str | int | float | bool
StandardTransformParams: TypeAlias = dict[str, PrimitiveParamValue]


class ProfileConfig(TypedDict):
    type: str
    params: NotRequired[dict[str, str | int | float | bool]]


class GeologicalTransformParams(TypedDict):
    profile: ProfileConfig
    dimension: str
    max_deviation: float


TransformParams: TypeAlias = StandardTransformParams | GeologicalTransformParams


class TransformConfig(TypedDict):
    name: str
    params: NotRequired[TransformParams]


TransformSpec: TypeAlias = str | TransformConfig


class PhraseConfig(TypedDict):
    motifs: list[str]
    transforms: NotRequired[list[TransformSpec]]


class VoiceConfig(TypedDict):
    phrases: list[PhraseConfig]


class CompositionConfig(TypedDict, total=False):
    voices: list[VoiceConfig]
    score_transforms: list[TransformSpec]


class CompositionDocument(TypedDict, total=False):
    motifs: dict[str, list[str]]
    composition: CompositionConfig
