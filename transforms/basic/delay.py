from collections.abc import Mapping
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import FloatParam, PhraseTransformContext, ToneSequence, TransformParamFieldSpec, TransformParamsSpec
from transforms.basic.pad_silence import pad_silence_tones


@dataclass(frozen=True)
class DelayParams:
    seconds: float


def _create_delay_params(parsed_params: Mapping[str, object]) -> DelayParams:
    seconds = parsed_params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (float, int)):
        raise ValueError("Param 'seconds' must be a float.")
    return DelayParams(seconds=float(seconds))


DELAY_PARAMS_SPEC = TransformParamsSpec[DelayParams](
    params_factory=_create_delay_params,
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


def delay_phrase_transform(context: PhraseTransformContext, params: DelayParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    delayed_tones = delay_tones(phrase_tones, seconds=params.seconds)
    return Phrase(motifs=[Motif(name="<transformed>", tones=delayed_tones)])


def delay_score_transform(score: Score, params: DelayParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        delayed_tones = delay_tones(voice_tones, seconds=params.seconds)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=delayed_tones)])]))

    return Score(voices=new_voices)
