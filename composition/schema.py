from collections.abc import Mapping
from typing import NotRequired, Required, TypeAlias, TypedDict

MotifsConfigInput: TypeAlias = dict[str, list[str]]


class TransformConfigInput(TypedDict, total=False):
    comment: str
    name: str
    params: Mapping[str, object]


class TransformConfig(TypedDict):
    name: str
    params: Mapping[str, object]


class PhraseConfigInput(TypedDict, total=False):
    comment: str
    motifs: list[str]
    transforms: NotRequired[list[TransformConfigInput]]


class PhraseConfig(TypedDict):
    motifs: list[str]
    transforms: list[TransformConfig]


class VoiceConfigInput(TypedDict, total=False):
    comment: str
    name: str
    phrases: list[PhraseConfigInput]


class VoiceConfig(TypedDict):
    phrases: list[PhraseConfig]


class CompositionConfigInput(TypedDict, total=False):
    voices: list[VoiceConfigInput]
    score_transforms: list[TransformConfigInput]


class CompositionConfig(TypedDict):
    voices: list[VoiceConfig]
    score_transforms: list[TransformConfig]


class ScoreDocumentInput(TypedDict, total=False):
    motifs: MotifsConfigInput
    voices: list[VoiceConfigInput]
    score_transforms: list[TransformConfigInput]


class ScoreDocument(TypedDict):
    motifs: MotifsConfigInput
    voices: list[VoiceConfig]
    score_transforms: list[TransformConfig]


class CompositionDocumentInput(TypedDict, total=False):
    name: Required[str]
    description: str
    document_version: int
    score: ScoreDocumentInput


class CompositionDocument(TypedDict):
    name: str
    description: NotRequired[str]
    document_version: int
    score: ScoreDocument
