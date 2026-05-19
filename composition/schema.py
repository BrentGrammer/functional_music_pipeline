from typing import NotRequired, TypedDict


class TransformConfigInput(TypedDict, total=False):
    name: str
    params: dict[str, object]


class TransformConfig(TypedDict):
    name: str
    params: dict[str, object]


class PhraseConfigInput(TypedDict, total=False):
    motifs: list[str]
    transforms: NotRequired[list[TransformConfigInput]]


class PhraseConfig(TypedDict):
    motifs: list[str]
    transforms: list[TransformConfig]


class VoiceConfig(TypedDict):
    phrases: list[PhraseConfigInput]


class CompositionConfig(TypedDict, total=False):
    voices: list[VoiceConfig]
    score_transforms: list[TransformConfigInput]


class CompositionDocument(TypedDict, total=False):
    motifs: dict[str, list[str]]
    composition: CompositionConfig
