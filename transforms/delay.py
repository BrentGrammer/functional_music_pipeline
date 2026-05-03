from score_model.tone_utils import make_silence_tone
from transforms.base import ToneSequence


def delay_tones(tones: ToneSequence, delay: float) -> ToneSequence:
    if delay < 0:
        raise ValueError("Delay must be non-negative. Negative offsets are not supported.")
    if delay == 0:
        return tones[:]

    silent_tone = make_silence_tone(delay)
    return [silent_tone] + tones[:]
