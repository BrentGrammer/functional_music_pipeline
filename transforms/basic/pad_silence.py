from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.tone_utils import make_silence_tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import EnumParam, FloatParam, ParsedTransformParams, PhraseTransformContext, TransformParamFieldSpec, TransformParamsSpec


@dataclass(frozen=True)
class PadSilenceParams:
    seconds: float
    position: str


def _create_pad_silence_params(parsed_params: ParsedTransformParams) -> PadSilenceParams:
    return PadSilenceParams(
        seconds=parsed_params.required("seconds", float),
        position=parsed_params.required("position", str),
    )


PAD_SILENCE_PARAMS_SPEC = TransformParamsSpec[PadSilenceParams](
    params_factory=_create_pad_silence_params,
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


def pad_silence_tones(tones: list[Tone], seconds: float, position: str) -> list[Tone]:
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


def pad_silence_phrase_transform(context: PhraseTransformContext, params: PadSilenceParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    padded_tones = pad_silence_tones(phrase_tones, seconds=params.seconds, position=params.position)
    return Phrase(motifs=[Motif(name="<transformed>", tones=padded_tones)])


def pad_silence_score_transform(score: Score, params: PadSilenceParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        padded_tones = pad_silence_tones(voice_tones, seconds=params.seconds, position=params.position)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=padded_tones)])]))

    return Score(voices=new_voices)
