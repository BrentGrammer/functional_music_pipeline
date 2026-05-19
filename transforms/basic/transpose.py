from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.pitch_utils import transpose_frequency_by_semitones
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import FloatParam, PhraseTransformContext, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

TRANSPOSE_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "semitones": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        )
    }
)


def transpose_tones(tones: ToneSequence, semitones: float) -> ToneSequence:
    return [
        Tone(
            frequency=transpose_frequency_by_semitones(t.frequency, semitones) if t.frequency > 0 else 0,
            duration=t.duration,
            sample_rate=t.sample_rate,
            amplitude=t.amplitude,
        )
        for t in tones
    ]


def transpose_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    semitones = params["semitones"]
    if isinstance(semitones, bool) or not isinstance(semitones, (int, float)):
        raise ValueError("Param 'semitones' must be a float.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    transposed_tones = transpose_tones(phrase_tones, semitones=float(semitones))
    return Phrase(motifs=[Motif(name="<transformed>", tones=transposed_tones)])


def transpose_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    semitones = params["semitones"]
    if isinstance(semitones, bool) or not isinstance(semitones, (int, float)):
        raise ValueError("Param 'semitones' must be a float.")

    return Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="<each_voice>",
                                tones=transpose_tones(
                                    flatten_voice_tones(voice),
                                    semitones=float(semitones),
                                ),
                            )
                        ]
                    )
                ]
            )
            for voice in score.voices
        ]
    )
