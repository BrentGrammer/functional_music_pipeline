from collections.abc import Mapping

from score_model.score import Score
from score_model.phrase import Phrase
from transforms.basic.pad_silence import pad_silence_phrase_transform, pad_silence_score_transform, pad_silence_tones
from transforms.base import FloatParam, PhraseTransformContext, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

DELAY_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "seconds": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        )
    }
)


def delay_tones(tones: ToneSequence, seconds: float) -> ToneSequence:
    if seconds < 0:
        raise ValueError("Delay must be non-negative. Negative offsets are not supported.")
    return pad_silence_tones(tones, seconds=seconds, position="start")


def delay_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")

    return pad_silence_phrase_transform(context, {"seconds": seconds, "position": "start"})


def delay_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")

    return pad_silence_score_transform(score, {"seconds": seconds, "position": "start"})
