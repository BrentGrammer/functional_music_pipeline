from typing import TypeAlias

from score_model.tone import Tone
from transforms.base import ToneDimension, parse_dimension
from transforms.profiles import CellularAutomataProfile, RandomDropProfile, RidgedMultifractalProfile, StochasticProfile, TerracedBrownianProfile, WeierstrassProfile

ToneSequence: TypeAlias = list[Tone]


def _modulate_tone_dimension(
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


def apply_stochastic_profile(
    tones: ToneSequence, profile: StochasticProfile, dimension: ToneDimension | str, max_deviation: float
) -> ToneSequence:
    """
    Applies a stochastic profile to a specific dimension of a tone sequence.
    """
    if not tones:
        return []

    dim = parse_dimension(dimension)
    profile_values = profile.generate(len(tones))
    return _modulate_tone_dimension(tones, profile_values, dim, max_deviation)


def apply_weierstrass_transform(
    tones: ToneSequence, dimension: ToneDimension | str, max_deviation: float,
    seed: int = 42, amplitude_scaling: float = 0.5, ripples_per_wave: float = 3.0, iterations: int = 10
) -> ToneSequence:
    profile = WeierstrassProfile(seed=seed, amplitude_scaling=amplitude_scaling, ripples_per_wave=ripples_per_wave, iterations=iterations)
    return apply_stochastic_profile(tones, profile, dimension, max_deviation)


def apply_terraced_drift_transform(
    tones: ToneSequence, dimension: ToneDimension | str, max_deviation: float,
    seed: int = 42, step_size: float = 0.25, quantize_resolution: float = 0.2
) -> ToneSequence:
    profile = TerracedBrownianProfile(seed=seed, step_size=step_size, quantize_resolution=quantize_resolution)
    return apply_stochastic_profile(tones, profile, dimension, max_deviation)


def apply_cellular_automata_transform(
    tones: ToneSequence, dimension: ToneDimension | str, max_deviation: float,
    rule: int = 30, seed: int = 42, width: int = 31
) -> ToneSequence:
    profile = CellularAutomataProfile(rule=rule, seed=seed, width=width)
    return apply_stochastic_profile(tones, profile, dimension, max_deviation)


def apply_ridged_drop_transform(
    tones: ToneSequence, dimension: ToneDimension | str, max_deviation: float,
    seed: int = 42, octaves: int = 3, ridge_density: float = 0.3, drop_when_noise_above: float = 0.5
) -> ToneSequence:
    profile = RidgedMultifractalProfile(
        seed=seed, octaves=octaves, ridge_density=ridge_density, drop_when_noise_above=drop_when_noise_above
    )
    return apply_stochastic_profile(tones, profile, dimension, max_deviation)


def apply_random_drop_transform(
    tones: ToneSequence, dimension: ToneDimension | str, max_deviation: float,
    seed: int = 42, drop_rate: float = 0.2
) -> ToneSequence:
    profile = RandomDropProfile(seed=seed, drop_rate=drop_rate)
    return apply_stochastic_profile(tones, profile, dimension, max_deviation)
