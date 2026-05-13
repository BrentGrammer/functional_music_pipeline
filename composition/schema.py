from typing import NotRequired, TypeAlias, TypedDict


class ProfileConfig(TypedDict):
    type: str
    params: NotRequired[dict[str, str | int | float | bool]]


class TransformConfig(TypedDict):
    name: str
    params: NotRequired[dict[str, object]]


TransformSpec: TypeAlias = TransformConfig


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
