from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.pitch_utils import transpose_frequency_by_semitones
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import FloatParam, ParsedTransformParams, PhraseTransformContext, TransformParamFieldSpec, TransformParamsSpec


@dataclass(frozen=True)
class TransposeParams:
    semitones: float


def _create_transpose_params(parsed_params: ParsedTransformParams) -> TransposeParams:
    return TransposeParams(semitones=parsed_params.required("semitones", float))


TRANSPOSE_PARAMS_SPEC = TransformParamsSpec[TransposeParams](
    params_factory=_create_transpose_params,
    fields={
        "semitones": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        )
    }
)


def transpose_tones(tones: list[Tone], semitones: float) -> list[Tone]:
    return [
        Tone(
            frequency=transpose_frequency_by_semitones(t.frequency, semitones) if t.frequency > 0 else 0,
            duration=t.duration,
            sample_rate=t.sample_rate,
            amplitude=t.amplitude,
        )
        for t in tones
    ]


def transpose_phrase_transform(context: PhraseTransformContext, params: TransposeParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    transposed_tones = transpose_tones(phrase_tones, semitones=params.semitones)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transposed_tones)])


def transpose_score_transform(score: Score, params: TransposeParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        transposed_tones = transpose_tones(voice_tones, semitones=params.semitones)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transposed_tones)])]))

    return Score(voices=new_voices)
