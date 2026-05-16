import random

from score_model.tone import Tone
from transforms.base import (
    EnumParam,
    FloatParam,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)

INTENSITY_LEVELS: dict[str, float] = {
    "none": 0.0,
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "extreme": 1.0,
}


def build_tempo_change_params_spec() -> TransformParamsSpec:
    intensity_schema = (EnumParam(allowed_values=tuple(INTENSITY_LEVELS)), FloatParam())
    return TransformParamsSpec(
        fields={
            "strength": TransformParamFieldSpec(
                required=True,
                schema=intensity_schema,
            ),
            "jaggedness": TransformParamFieldSpec(
                schema=intensity_schema,
            ),
        }
    )


def resolve_strength(value: object = "medium") -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"Invalid strength: {repr(value)}. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
        )
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value not in INTENSITY_LEVELS:
            raise ValueError(
                f"Invalid strength: '{value}'. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
            )
        return INTENSITY_LEVELS[lower_value]
    if isinstance(value, (int, float)):
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"Invalid strength: {value}. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
            )
        return float(value)
    raise ValueError(
        f"Invalid strength: {repr(value)}. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
    )


def resolve_jaggedness(value: object = "none") -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"Invalid jaggedness: {repr(value)}. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
        )
    if isinstance(value, str):
        lower_value = value.lower()
        if lower_value not in INTENSITY_LEVELS:
            raise ValueError(
                f"Invalid jaggedness: '{value}'. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
            )
        return INTENSITY_LEVELS[lower_value]
    if isinstance(value, (int, float)):
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"Invalid jaggedness: {value}. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
            )
        return float(value)
    raise ValueError(
        f"Invalid jaggedness: {repr(value)}. Use one of none, low, medium, high, extreme, or a number from 0.0 to 1.0."
    )


def compute_tempo_change_factors(tone_count: int, start_factor: float, end_factor: float) -> list[float]:
    if tone_count == 0:
        return []
    if tone_count == 1:
        return [1.0]
    factors = []
    for i in range(tone_count):
        progress = i / (tone_count - 1)
        factor = start_factor + (end_factor - start_factor) * progress
        factors.append(factor)
    return factors


def apply_duration_multipliers(tones: ToneSequence, multipliers: list[float]) -> ToneSequence:
    MIN_DURATION_SECONDS = 0.001

    if len(tones) != len(multipliers):
        raise ValueError(
            f"Tone count ({len(tones)}) must match multiplier count ({len(multipliers)})."
        )
    return [
        Tone(
            frequency=tone.frequency,
            duration=max(MIN_DURATION_SECONDS, tone.duration * multiplier),
            sample_rate=tone.sample_rate,
            amplitude=tone.amplitude,
        )
        for tone, multiplier in zip(tones, multipliers)
    ]


def compute_jaggedness_weights(
    tone_count: int,
    resolved_jaggedness: float,
    random_source: random.Random | None = None,
) -> list[float]:
    if tone_count == 0:
        return []

    if resolved_jaggedness == 0.0:
        return [1.0] * tone_count

    max_weight_range = 0.5
    weight_range = resolved_jaggedness * max_weight_range

    rng = random_source if random_source is not None else random

    weights = []
    for _ in range(tone_count):
        offset = rng.uniform(-weight_range, weight_range)
        weights.append(1.0 + offset)

    return weights
