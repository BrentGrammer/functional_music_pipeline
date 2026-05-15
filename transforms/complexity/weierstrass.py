import math
import random
from dataclasses import dataclass

from score_model.tone import Tone
from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)

_DIMENSION_FIELD = TransformParamFieldSpec(
    required=True,
    schema=EnumParam(allowed_values=tuple(ToneDimension)),
)
_MAX_DEVIATION_FIELD = TransformParamFieldSpec(
    required=True,
    schema=FloatParam(),
)


def _build_params_spec(
    extra_fields: dict[str, TransformParamFieldSpec],
) -> TransformParamsSpec:
    return TransformParamsSpec(
        fields={
            "dimension": _DIMENSION_FIELD,
            "max_deviation": _MAX_DEVIATION_FIELD,
            **extra_fields,
        }
    )


WEIERSTRASS_PARAMS_SPEC = _build_params_spec(
    {
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


def _apply_profile(
    tones: ToneSequence,
    profile: _WeierstrassProfile,
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


def apply_weierstrass_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    max_deviation: float,
    seed: int = 42,
    amplitude_scaling: float = 0.5,
    ripples_per_wave: float = 3.0,
    iterations: int = 10,
) -> ToneSequence:
    return _apply_profile(
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
