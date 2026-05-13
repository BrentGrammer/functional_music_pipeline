from typing import TypeAlias

from score_model.tone import Tone
from transforms.base import ToneDimension, parse_dimension
from transforms.profiles import StochasticProfile

ToneSequence: TypeAlias = list[Tone]


def _apply_stochastic_profile(
    tones: ToneSequence, profile: list[float], dimension: ToneDimension, max_deviation: float
) -> ToneSequence:
    """
    Applies a sequence of normalized values (-1.0 to 1.0) to a specific dimension of a tone sequence.
    max_deviation determines the maximum percentage deviation (e.g., 0.1 = +/- 10%).
    """
    result = []
    for tone, value in zip(tones, profile):
        scale = 1.0 + (value * max_deviation)

        if dimension == ToneDimension.FREQUENCY:
            new_freq = max(1.0, tone.frequency * scale)
            result.append(Tone(new_freq, tone.duration, tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.DURATION:
            new_dur = max(0.001, tone.duration * scale)
            result.append(Tone(tone.frequency, new_dur, tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.AMPLITUDE:
            new_amp = max(0.0, min(1.0, tone.amplitude * scale))
            result.append(Tone(tone.frequency, tone.duration, tone.sample_rate, new_amp))

    return result


def apply_geological_transform(
    tones: ToneSequence, profile: StochasticProfile, dimension: ToneDimension | str, max_deviation: float
) -> ToneSequence:
    """
    Applies a stochastic profile to a specific dimension of a tone sequence.
    """
    if not tones:
        return []

    dim = parse_dimension(dimension)
    profile_values = profile.generate(len(tones))
    return _apply_stochastic_profile(tones, profile_values, dim, max_deviation)
