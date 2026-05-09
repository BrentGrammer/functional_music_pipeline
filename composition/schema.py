from typing import TypedDict, NotRequired, TypeAlias


class ProfileConfig(TypedDict):
    type: str
    params: NotRequired[dict[str, str | int | float | bool]]


class GeologicalTransformParams(TypedDict):
    profile: ProfileConfig
    dimension: str
    max_deviation: float


TransformParams: TypeAlias = dict[str, str | int | float | bool] | GeologicalTransformParams


class TransformConfig(TypedDict, total=False):
    name: str
    params: TransformParams


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
