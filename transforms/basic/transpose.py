from score_model.pitch_utils import transpose_frequency_by_semitones
from score_model.tone import Tone
from transforms.base import FloatParam, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

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
