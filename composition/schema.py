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


class VoiceConfigInput(TypedDict):
    phrases: list[PhraseConfigInput]


class VoiceConfig(TypedDict):
    phrases: list[PhraseConfig]


class CompositionConfigInput(TypedDict, total=False):
    voices: list[VoiceConfigInput]
    score_transforms: list[TransformConfigInput]


class CompositionConfig(TypedDict):
    voices: list[VoiceConfig]
    score_transforms: list[TransformConfig]


class CompositionDocumentInput(TypedDict, total=False):
    motifs: dict[str, list[str]]
    composition: CompositionConfigInput


class CompositionDocument(TypedDict):
    motifs: dict[str, list[str]]
    composition: CompositionConfig
