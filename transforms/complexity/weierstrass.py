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
from transforms.complexity._modulation import apply_profile

_WEIERSTRASS_INTENSITY_PRESETS = {
    "low": {"max_deviation": 0.05, "amplitude_scaling": 0.3, "ripples_per_wave": 2.0, "iterations": 6},
    "medium": {"max_deviation": 0.15, "amplitude_scaling": 0.5, "ripples_per_wave": 3.0, "iterations": 10},
    "high": {"max_deviation": 0.25, "amplitude_scaling": 0.6, "ripples_per_wave": 4.0, "iterations": 12},
    "extreme": {"max_deviation": 0.4, "amplitude_scaling": 0.8, "ripples_per_wave": 6.0, "iterations": 18},
}


def _resolve_intensity(value: str) -> dict:
    if not isinstance(value, str):
        raise ValueError(f"Intensity must be a string, got {type(value).__name__}")
    if value not in _WEIERSTRASS_INTENSITY_PRESETS:
        raise ValueError(
            f"Invalid intensity '{value}'. Must be one of: {', '.join(_WEIERSTRASS_INTENSITY_PRESETS.keys())}"
        )
    return _WEIERSTRASS_INTENSITY_PRESETS[value]


WEIERSTRASS_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "intensity": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(_WEIERSTRASS_INTENSITY_PRESETS.keys())),
        ),
    }
)


@dataclass(frozen=True)
class _WeierstrassProfile:
    seed: int = 42
    amplitude_scaling: float = 0.5
    ripples_per_wave: float = 3.0
    iterations: int = 10

    def generate(self, length: int) -> list[float]:
        random.seed(self.seed)
        start_x = random.uniform(0.0, 100.0)
        step = 0.15

        max_val = sum(self.amplitude_scaling**n for n in range(self.iterations))
        if max_val == 0:
            max_val = 1.0

        profile = []
        for i in range(length):
            x = start_x + (i * step)
            val = 0.0
            for n in range(self.iterations):
                val += (self.amplitude_scaling**n) * math.cos((self.ripples_per_wave**n) * math.pi * x)
            profile.append(val / max_val)

        return profile


def apply_weierstrass_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    intensity: str,
) -> ToneSequence:
    preset = _resolve_intensity(intensity)
    return apply_profile(
        tones,
        _WeierstrassProfile(
            seed=42,
            amplitude_scaling=preset["amplitude_scaling"],
            ripples_per_wave=preset["ripples_per_wave"],
            iterations=preset["iterations"],
        ),
        dimension,
        preset["max_deviation"],
    )
