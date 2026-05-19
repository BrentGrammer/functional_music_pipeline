from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone_utils import make_silence_tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
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
    if seconds == 0:
        return tones[:]

    silent_tone = make_silence_tone(seconds)
    return [silent_tone] + tones[:]


def delay_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    delayed_tones = delay_tones(phrase_tones, seconds=float(seconds))
    return Phrase(motifs=[Motif(name="<transformed>", tones=delayed_tones)])


def delay_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        delayed_tones = delay_tones(voice_tones, seconds=float(seconds))
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=delayed_tones)])]))

    return Score(voices=new_voices)
