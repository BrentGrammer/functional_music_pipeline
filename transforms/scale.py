from score_model.tone import Tone
from transforms.base import (
    EnumParam,
    FloatParam,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)

SCALE_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "factor": TransformParamFieldSpec(
            schema=FloatParam(),
            required=True,
        ),
    }
)


def scale_transform(tones: ToneSequence, dimension: ToneDimension | str, factor: float) -> ToneSequence:
    """
    Scales a specific dimension of a tone sequence by a given factor.
    """
    if not tones:
        return []

    dim = parse_dimension(dimension)
    result = []
    for t in tones:
        if dim == ToneDimension.FREQUENCY:
            new_val = max(1.0, t.frequency * factor)
            result.append(Tone(new_val, t.duration, t.sample_rate, t.amplitude))
        elif dim == ToneDimension.DURATION:
            new_val = max(0.0, t.duration * factor)
            result.append(Tone(t.frequency, new_val, t.sample_rate, t.amplitude))
        elif dim == ToneDimension.AMPLITUDE:
            new_val = max(0.0, min(1.0, t.amplitude * factor))
            result.append(Tone(t.frequency, t.duration, t.sample_rate, new_val))
            
    return result
