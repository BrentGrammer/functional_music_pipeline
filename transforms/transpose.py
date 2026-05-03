from score_model.pitch_utils import semitones_to_frequency
from score_model.tone import Tone
from transforms.base import ToneSequence


def transpose_tones(tones: ToneSequence, semitones: float) -> ToneSequence:
    return [
        Tone(
            frequency=semitones_to_frequency(t.frequency, semitones) if t.frequency > 0 else 0,
            duration=t.duration,
            sample_rate=t.sample_rate,
            amplitude=t.amplitude,
        )
        for t in tones
    ]
