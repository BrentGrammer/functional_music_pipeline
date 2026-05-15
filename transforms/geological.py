from typing import TypeAlias

from score_model.tone import Tone
from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    ToneDimension,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)
from transforms.profiles import (
    CellularAutomataProfile,
    RandomDropProfile,
    RidgedMultifractalProfile,
    StochasticProfile,
    TerracedBrownianProfile,
    WeierstrassProfile,
)

ToneSequence: TypeAlias = list[Tone]

_DIMENSION_FIELD = TransformParamFieldSpec(
    required=True,
    schema=EnumParam(allowed_values=tuple(ToneDimension)),
)
_MAX_DEVIATION_FIELD = TransformParamFieldSpec(
    required=True,
    schema=FloatParam(),
)


def _build_stochastic_params_spec(
    extra_fields: dict[str, TransformParamFieldSpec],
) -> TransformParamsSpec:
    return TransformParamsSpec(
        fields={
            "dimension": _DIMENSION_FIELD,
            "max_deviation": _MAX_DEVIATION_FIELD,
            **extra_fields,
        }
    )


WEIERSTRASS_PARAMS_SPEC = _build_stochastic_params_spec(
    {
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "amplitude_scaling": TransformParamFieldSpec(schema=FloatParam()),
        "ripples_per_wave": TransformParamFieldSpec(schema=FloatParam()),
        "iterations": TransformParamFieldSpec(schema=IntegerParam()),
    }
)
TERRACED_DRIFT_PARAMS_SPEC = _build_stochastic_params_spec(
    {
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "step_size": TransformParamFieldSpec(schema=FloatParam()),
        "quantize_resolution": TransformParamFieldSpec(schema=FloatParam()),
    }
)
CELLULAR_AUTOMATA_PARAMS_SPEC = _build_stochastic_params_spec(
    {
        "rule": TransformParamFieldSpec(schema=IntegerParam()),
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "width": TransformParamFieldSpec(schema=IntegerParam()),
    }
)
RIDGED_DROP_PARAMS_SPEC = _build_stochastic_params_spec(
    {
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "octaves": TransformParamFieldSpec(schema=IntegerParam()),
        "ridge_density": TransformParamFieldSpec(schema=FloatParam()),
        "drop_when_noise_above": TransformParamFieldSpec(schema=FloatParam()),
    }
)
RANDOM_DROP_PARAMS_SPEC = _build_stochastic_params_spec(
    {
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "drop_rate": TransformParamFieldSpec(schema=FloatParam()),
    }
)


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
