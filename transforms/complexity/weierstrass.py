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

WEIERSTRASS_PARAMS_SPEC = TransformParamsSpec(
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
        "amplitude_scaling": TransformParamFieldSpec(schema=FloatParam()),
        "ripples_per_wave": TransformParamFieldSpec(schema=FloatParam()),
        "iterations": TransformParamFieldSpec(schema=IntegerParam()),
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
    max_deviation: float,
    seed: int = 42,
    amplitude_scaling: float = 0.5,
    ripples_per_wave: float = 3.0,
    iterations: int = 10,
) -> ToneSequence:
    return apply_profile(
        tones,
        _WeierstrassProfile(
            seed=seed,
            amplitude_scaling=amplitude_scaling,
            ripples_per_wave=ripples_per_wave,
            iterations=iterations,
        ),
        dimension,
        max_deviation,
    )
