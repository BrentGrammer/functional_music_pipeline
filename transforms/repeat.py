from transforms.base import ToneSequence


def repeat_tones(tones: ToneSequence, count: int) -> ToneSequence:
    if count < 1:
        raise ValueError("Repeat count must be at least 1.")

    return tones * (count + 1)
