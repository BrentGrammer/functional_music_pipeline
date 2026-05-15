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


RANDOM_DROP_PARAMS_SPEC = _build_params_spec(
    {
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "drop_rate": TransformParamFieldSpec(schema=FloatParam()),
    }
)


@dataclass(frozen=True)
class _RandomDropProfile:
    seed: int = 42
    drop_rate: float = 0.2

    def generate(self, length: int) -> list[float]:
        rng = random.Random(self.seed)
        profile = []
        for _ in range(length):
            if rng.random() < self.drop_rate:
                profile.append(-rng.random())
            else:
                profile.append(0.0)
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
    profile: _RandomDropProfile,
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


def apply_random_drop_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    max_deviation: float,
    seed: int = 42,
    drop_rate: float = 0.2,
) -> ToneSequence:
    return _apply_profile(
        tones,
        _RandomDropProfile(seed=seed, drop_rate=drop_rate),
        dimension,
        max_deviation,
    )
