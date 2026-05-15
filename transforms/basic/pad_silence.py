from score_model.tone_utils import make_silence_tone
from transforms.base import EnumParam, FloatParam, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

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
