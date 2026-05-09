from score_model.tone_utils import make_silence_tone
from transforms.base import ToneSequence


def delay_tones(tones: ToneSequence, seconds: float) -> ToneSequence:
    if seconds < 0:
        raise ValueError("Delay must be non-negative. Negative offsets are not supported.")
    if seconds == 0:
        return tones[:]

    silent_tone = make_silence_tone(seconds)
    return [silent_tone] + tones[:]
