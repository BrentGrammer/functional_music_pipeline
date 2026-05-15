from typing import Protocol

from score_model.tone import Tone
from transforms.base import (
    ToneDimension,
    ToneSequence,
    parse_dimension,
)


class _GeneratedProfile(Protocol):
    def generate(self, length: int) -> list[float]: ...


def _modulate_tone_dimension(
    tones: ToneSequence,
    profile: list[float],
    dimension: ToneDimension,
    max_deviation: float,
) -> ToneSequence:
    result = []
    for tone, value in zip(tones, profile):
        scale = 1.0 + (value * max_deviation)

        if dimension == ToneDimension.FREQUENCY:
            result.append(Tone(max(1.0, tone.frequency * scale), tone.duration, tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.DURATION:
            result.append(Tone(tone.frequency, max(0.001, tone.duration * scale), tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.AMPLITUDE:
            result.append(Tone(tone.frequency, tone.duration, tone.sample_rate, max(0.0, min(1.0, tone.amplitude * scale))))

    return result


def apply_profile(
    tones: ToneSequence,
    profile: _GeneratedProfile,
    dimension: ToneDimension | str,
    max_deviation: float,
) -> ToneSequence:
    if not tones:
        return []

    resolved_dimension = parse_dimension(dimension)
    return _modulate_tone_dimension(
        tones,
        profile.generate(len(tones)),
        resolved_dimension,
        max_deviation,
    )
