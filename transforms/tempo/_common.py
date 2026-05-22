import random
from dataclasses import dataclass

from score_model.tone import Tone
from transforms.base import (
    EnumParam,
    FloatParam,
    ParsedTransformParams,
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


@dataclass(frozen=True)
class TempoChangeParams:
    strength: float
    jaggedness: float


def _resolve_intensity(value: object) -> float:
    if isinstance(value, str):
        return INTENSITY_LEVELS[value.lower()]
    val = float(value)  # type: ignore[arg-type]
    if not (0.0 <= val <= 1.0):
        raise ValueError(f"Intensity float must be between 0.0 and 1.0, got {val}")
    return val


def _tempo_change_params_factory(parsed: ParsedTransformParams) -> TempoChangeParams:
    strength_raw = parsed.required("strength", object)
    jaggedness_raw = parsed.required("jaggedness", object)
    return TempoChangeParams(
        strength=_resolve_intensity(strength_raw),
        jaggedness=_resolve_intensity(jaggedness_raw),
    )


def build_tempo_change_params_spec() -> TransformParamsSpec[TempoChangeParams]:
    intensity_schema = (EnumParam(allowed_values=tuple(INTENSITY_LEVELS)), FloatParam())
    return TransformParamsSpec[TempoChangeParams](
        fields={
            "strength": TransformParamFieldSpec(
                schema=intensity_schema,
                default="medium",
            ),
            "jaggedness": TransformParamFieldSpec(
                schema=intensity_schema,
                default="none",
            ),
        },
        params_factory=_tempo_change_params_factory,
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
