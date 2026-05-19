from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone_utils import make_silence_tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import EnumParam, FloatParam, PhraseTransformContext, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

PAD_SILENCE_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "seconds": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
        "position": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=("start", "end")),
        ),
    }
)


def pad_silence_tones(tones: ToneSequence, seconds: float, position: str) -> ToneSequence:
    if seconds < 0:
        raise ValueError("Pad silence seconds must be non-negative.")
    if position not in {"start", "end"}:
        raise ValueError("Pad silence position must be 'start' or 'end'.")
    if seconds == 0:
        return tones[:]

    silent_tone = make_silence_tone(seconds)
    if position == "start":
        return [silent_tone] + tones[:]

    return tones[:] + [silent_tone]


def pad_silence_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")

    position = params["position"]
    if not isinstance(position, str):
        raise ValueError("Param 'position' must be a string.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    padded_tones = pad_silence_tones(phrase_tones, seconds=float(seconds), position=position)
    return Phrase(motifs=[Motif(name="<transformed>", tones=padded_tones)])


def pad_silence_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    seconds = params["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("Param 'seconds' must be a float.")

    position = params["position"]
    if not isinstance(position, str):
        raise ValueError("Param 'position' must be a string.")

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        padded_tones = pad_silence_tones(voice_tones, seconds=float(seconds), position=position)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=padded_tones)])]))

    return Score(voices=new_voices)
