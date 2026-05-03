from transforms.base import ToneSequence


def reverse_tones(tones: ToneSequence) -> ToneSequence:
    return tones[::-1]
