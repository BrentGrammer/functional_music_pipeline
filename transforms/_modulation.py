from score_model.tone import Tone
from transforms.base import (
    ToneDimension,
)


def apply_fluctuations(
    tones: list[Tone],
    fluctuations: list[float],
    dimension: ToneDimension,
    max_deviation: float,
) -> list[Tone]:
    """
    Apply per-tone fluctuation to a single dimension (frequency, duration, or amplitude).

    Each fluctuation value in [-1.0, 1.0] scales the corresponding tone's dimension
    by ``1.0 + (value * max_deviation)``. This allows transforms to generate a raw
    list of fluctuation values and apply them directly.
    """
    result: list[Tone] = []
    for tone, value in zip(tones, fluctuations):
        scale = 1.0 + (value * max_deviation)

        if dimension == ToneDimension.FREQUENCY:
            result.append(Tone(max(1.0, tone.frequency * scale), tone.duration, tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.DURATION:
            result.append(Tone(tone.frequency, max(0.001, tone.duration * scale), tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.AMPLITUDE:
            result.append(Tone(tone.frequency, tone.duration, tone.sample_rate, max(0.0, min(1.0, tone.amplitude * scale))))

    return result
