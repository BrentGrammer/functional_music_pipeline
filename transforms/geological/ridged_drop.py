import math
import random
from dataclasses import dataclass

from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.geological._modulation import apply_profile

_RIDGED_DROP_DEPTH_LEVELS = {
    "none": 0.0,
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "extreme": 1.0,
}


def _resolve_drop_depth(value: str | float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"drop_depth must be a string or float, not boolean.")
    if isinstance(value, str):
        if value.lower() not in _RIDGED_DROP_DEPTH_LEVELS:
            allowed = ", ".join(_RIDGED_DROP_DEPTH_LEVELS.keys())
            raise ValueError(f"drop_depth must be one of: {allowed}.")
        return _RIDGED_DROP_DEPTH_LEVELS[value.lower()]
    if isinstance(value, (int, float)):
        if value < 0.0 or value > 1.0:
            raise ValueError(f"drop_depth must be between 0.0 and 1.0, got {value}.")
        return float(value)
    raise ValueError(f"drop_depth must be a string or float, not {type(value).__name__}.")


RIDGED_DROP_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "max_deviation": TransformParamFieldSpec(
            required=True,
            schema=FloatParam(),
        ),
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "octaves": TransformParamFieldSpec(schema=IntegerParam()),
        "ridge_density": TransformParamFieldSpec(schema=FloatParam()),
        "drop_when_noise_above": TransformParamFieldSpec(schema=FloatParam()),
    }
)


def _sample_ridged_noise(
    index: int,
    phases: list[float],
    rates: list[float],
    amplitudes: list[float],
) -> float:
    noise = 0.0
    weight = 1.0

    for octave_index in range(len(phases)):
        octave_value = 1.0 - abs(math.sin(index * rates[octave_index] + phases[octave_index]))
        octave_value *= weight
        weight = max(0.0, min(1.0, octave_value * 2.0))
        noise += octave_value * amplitudes[octave_index]

    return noise


@dataclass(frozen=True)
class _RidgedMultifractalProfile:
    seed: int = 42
    octaves: int = 3
    ridge_density: float = 0.3
    drop_when_noise_above: float = 0.5

    def generate(self, length: int) -> list[float]:
        rng = random.Random(self.seed)
        phases = [rng.uniform(0, 2 * math.pi) for _ in range(self.octaves)]

        rates = [self.ridge_density * (2 ** i) for i in range(self.octaves)]
        amplitudes = [1.0 / (2 ** i) for i in range(self.octaves)]

        max_possible = sum(amplitudes)
        if max_possible == 0:
            max_possible = 1.0

        threshold = self.drop_when_noise_above
        profile = []

        for index in range(length):
            noise = _sample_ridged_noise(index, phases, rates, amplitudes)
            normalized_noise = noise / max_possible

            if normalized_noise > threshold:
                if threshold < 1.0:
                    drop_intensity = -1.0 * ((normalized_noise - threshold) / (1.0 - threshold))
                else:
                    drop_intensity = -1.0
                profile.append(max(-1.0, drop_intensity))
            else:
                profile.append(0.0)

        return profile


def apply_ridged_drop_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    max_deviation: float,
    seed: int = 42,
    octaves: int = 3,
    ridge_density: float = 0.3,
    drop_when_noise_above: float = 0.5,
) -> ToneSequence:
    return apply_profile(
        tones,
        _RidgedMultifractalProfile(
            seed=seed,
            octaves=octaves,
            ridge_density=ridge_density,
            drop_when_noise_above=drop_when_noise_above,
        ),
        dimension,
        max_deviation,
    )
