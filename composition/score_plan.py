from dataclasses import dataclass, field
from collections.abc import Mapping

from score_model.motif import Motif


@dataclass(frozen=True)
class TransformRequest:
    name: str
    params: Mapping[str, object]


@dataclass(frozen=True)
class PhraseTransformRequest:
    voice_index: int
    phrase_index: int
    transform_request: TransformRequest


@dataclass(frozen=True)
class ScoreTransformRequest:
    transform_request: TransformRequest


@dataclass(frozen=True)
class PhrasePlan:
    motifs: list[Motif]


@dataclass(frozen=True)
class VoicePlan:
    phrases: list[PhrasePlan]


@dataclass(frozen=True)
class ScorePlan:
    motifs: dict[str, Motif] = field(default_factory=dict)
    voices: list[VoicePlan] = field(default_factory=list)
    phrase_transform_requests: list[PhraseTransformRequest] = field(default_factory=list)
    score_transform_requests: list[ScoreTransformRequest] = field(default_factory=list)
