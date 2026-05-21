from collections.abc import Mapping
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import IntegerParam, PhraseTransformContext, ToneSequence, TransformParamFieldSpec, TransformParamsSpec


@dataclass(frozen=True)
class RepeatParams:
    count: int


def _create_repeat_params(parsed_params: Mapping[str, object]) -> RepeatParams:
    count = parsed_params["count"]
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("Param 'count' must be an integer.")
    return RepeatParams(count=count)


REPEAT_PARAMS_SPEC = TransformParamsSpec[RepeatParams](
    params_factory=_create_repeat_params,
    fields={
        "count": TransformParamFieldSpec(
            schema=IntegerParam(),
            required=True,
        )
    }
)


def repeat_tones(tones: ToneSequence, count: int) -> ToneSequence:
    if count < 1:
        raise ValueError("Repeat count must be at least 1.")

    return tones * (count + 1)


def repeat_phrase_transform(context: PhraseTransformContext, params: RepeatParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    repeated_tones = repeat_tones(phrase_tones, count=params.count)
    return Phrase(motifs=[Motif(name="<transformed>", tones=repeated_tones)])


def repeat_score_transform(score: Score, params: RepeatParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        repeated_tones = repeat_tones(voice_tones, count=params.count)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=repeated_tones)])]))

    return Score(voices=new_voices)
