from transforms.base import ToneSequence, TransformParamsSpec

REVERSE_PARAMS_SPEC = TransformParamsSpec()


def reverse_tones(tones: ToneSequence) -> ToneSequence:
    return tones[::-1]
