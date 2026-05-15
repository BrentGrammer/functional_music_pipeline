from transforms.base import IntegerParam, ToneSequence, TransformParamFieldSpec, TransformParamsSpec

REPEAT_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "count": TransformParamFieldSpec(
            schema=IntegerParam(),
            required=True,
        )
    }
)


def repeat_tones(tones: ToneSequence, count: int) -> ToneSequence:
    if count < 1:
        raise ValueError("Repeat count must be at least 1.")

    return tones * (count + 1)
