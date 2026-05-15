import random

from score_model.math_constants import FEIGENBAUM_DELTA as FEIGENBAUM_RATIO
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
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
from transforms.scale import scale_transform

INTENSITY_LEVELS: dict[str, float] = {
    "none": 0.0,
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "extreme": 1.0,
}


def _build_tempo_change_params_spec() -> TransformParamsSpec:
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
            "seed": TransformParamFieldSpec(
                schema=IntegerParam(),
            ),
        }
    )


ACCELERANDO_PARAMS_SPEC = _build_tempo_change_params_spec()
RITARDANDO_PARAMS_SPEC = _build_tempo_change_params_spec()
FEIGENBAUM_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
    }
)


def _is_numeric_string(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


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
        if _is_numeric_string(value):
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
        if _is_numeric_string(value):
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


def _compute_tempo_change_factors(tone_count: int, start_factor: float, end_factor: float) -> list[float]:
    """
    Compute proportional duration multipliers for a tempo change (accelerando/ritardando).

    Each factor is multiplied against a tone's original duration:
        new_duration = original_duration * factor_at_index

    For accelerando, factors decrease (start=1.0, end=<1.0).
    For ritardando, factors increase (start=1.0, end=>1.0).
    """
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


def _interpolate_multiplier_at_position(
    position_index: int, total_tones: int, start_multiplier: float, end_multiplier: float
) -> float:
    """
    Compute the duration multiplier for a specific tone position in the phrase.

    For a phrase with 3 tones where start_multiplier=1.0 and end_multiplier=0.5:
        - Position 0 returns 1.0 (first tone, no change)
        - Position 1 returns 0.75 (middle tone, halfway between)
        - Position 2 returns 0.5 (last tone, full change applied)
    """
    if total_tones == 1:
        return 1.0
    progress = position_index / (total_tones - 1)
    return start_multiplier + (end_multiplier - start_multiplier) * progress


def _resolve_accelerando_final_duration_multiplier(strength: float) -> float:
    """
    Map public strength (0.0 to 1.0) to the duration multiplier for the final tone.

    At strength=0.0, multiplier=1.0 (no change).
    At strength=1.0, durations shrink to the minimum safe ratio.
    """
    MIN_DURATION_RATIO = 0.10
    NEUTRAL_MULTIPLIER = 1.0
    return NEUTRAL_MULTIPLIER - strength * (NEUTRAL_MULTIPLIER - MIN_DURATION_RATIO)


def _resolve_ritardando_final_duration_multiplier(strength: float) -> float:
    """
    Map public strength (0.0 to 1.0) to the duration multiplier for the final tone.

    At strength=0.0, multiplier=1.0 (no change).
    At strength=1.0, durations expand to the maximum ratio.
    No upper bound is enforced beyond this; existing total-duration
    safeguards handle extreme output.
    """
    NEUTRAL_MULTIPLIER = 1.0
    MAX_DURATION_RATIO = 4.0
    return NEUTRAL_MULTIPLIER + strength * (MAX_DURATION_RATIO - NEUTRAL_MULTIPLIER)


def _apply_duration_multipliers(tones: ToneSequence, multipliers: list[float]) -> ToneSequence:
    """
    Apply duration multipliers to each tone while preserving other properties.

    Each tone's duration is multiplied by the corresponding multiplier.
    Frequency, sample rate, and amplitude are preserved.
    Durations are clamped to a minimum positive value to prevent collapse.
    """
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


def _compute_jaggedness_weights(
    tone_count: int,
    resolved_jaggedness: float,
    random_source: random.Random | None = None,
) -> list[float]:
    """
    Compute stochastic multiplicative weights for jaggedness.

    At jaggedness=0.0, all weights are 1.0 (no variation).
    Higher jaggedness values produce wider variation in weights,
    allowing local duration reversals and asymmetry.

    For testing, pass a pre-seeded random.Random instance as random_source
    to produce deterministic output.
    """
    if tone_count == 0:
        return []

    if resolved_jaggedness == 0.0:
        return [1.0] * tone_count

    # At maximum jaggedness (1.0), weights can vary from 0.5x to 1.5x the smooth value.
    # This range is wide enough to create local duration reversals while keeping
    # durations positive. May be adjusted after listening tests.
    max_weight_range = 0.5
    weight_range = resolved_jaggedness * max_weight_range

    rng = random_source if random_source is not None else random

    weights = []
    for _ in range(tone_count):
        offset = rng.uniform(-weight_range, weight_range)
        weights.append(1.0 + offset)

    return weights


def accelerando_transform(
    tones: ToneSequence,
    strength: str | float = "medium",
    jaggedness: str | float = "none",
    seed: int | None = None,
) -> ToneSequence:
    """
    Apply an accelerando effect that gradually shortens durations across the phrase.

    Higher strength produces shorter durations toward the end of the phrase.
    Higher jaggedness adds stochastic variation, allowing local duration reversals.
    """
    if not tones:
        return []

    resolved_jaggedness = resolve_jaggedness(jaggedness)
    resolved_strength = resolve_strength(strength)

    random_source = random.Random(seed) if seed is not None else None

    final_duration_multiplier = _resolve_accelerando_final_duration_multiplier(resolved_strength)
    trend_multipliers = _compute_tempo_change_factors(len(tones), 1.0, final_duration_multiplier)
    jaggedness_weights = _compute_jaggedness_weights(len(tones), resolved_jaggedness, random_source)

    combined_multipliers = [
        trend * weight for trend, weight in zip(trend_multipliers, jaggedness_weights)
    ]

    return _apply_duration_multipliers(tones, combined_multipliers)


def ritardando_transform(
    tones: ToneSequence,
    strength: str | float = "medium",
    jaggedness: str | float = "none",
    seed: int | None = None,
) -> ToneSequence:
    """
    Apply a ritardando effect that gradually lengthens durations across the phrase.

    Higher strength produces longer durations toward the end of the phrase.
    Higher jaggedness adds stochastic variation, allowing local duration reversals.
    """
    if not tones:
        return []

    resolved_jaggedness = resolve_jaggedness(jaggedness)
    resolved_strength = resolve_strength(strength)

    random_source = random.Random(seed) if seed is not None else None

    final_duration_multiplier = _resolve_ritardando_final_duration_multiplier(resolved_strength)
    trend_multipliers = _compute_tempo_change_factors(len(tones), 1.0, final_duration_multiplier)
    jaggedness_weights = _compute_jaggedness_weights(len(tones), resolved_jaggedness, random_source)

    combined_multipliers = [
        trend * weight for trend, weight in zip(trend_multipliers, jaggedness_weights)
    ]

    return _apply_duration_multipliers(tones, combined_multipliers)


def _cumulative_dimension(tones: ToneSequence, dim: ToneDimension) -> float:
    dimension = dim.value
    return float(sum(getattr(t, dimension) for t in tones))


def feigenbaum_sequence(tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION) -> ToneSequence:
    if not tones:
        return []

    dim = parse_dimension(dimension)
    dim_attr = dim.name.lower()
    new_tones = [tones[0]]

    for tone in tones[1:]:
        previous = getattr(new_tones[-1], dim_attr)
        new_val = previous / FEIGENBAUM_RATIO

        freq = tone.frequency
        dur = tone.duration
        amp = tone.amplitude

        if dim == ToneDimension.FREQUENCY:
            freq = max(1.0, new_val)
        elif dim == ToneDimension.DURATION:
            dur = max(0.0, new_val)
        elif dim == ToneDimension.AMPLITUDE:
            amp = max(0.0, min(1.0, new_val))

        new_tones.append(Tone(frequency=freq, duration=dur, sample_rate=tone.sample_rate, amplitude=amp))

    return new_tones


def phrase_feigenbaum_shrink(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-feigenbaum-shrink: no preceding phrases exist to relate to.")

    dim = parse_dimension(dimension)
    previous = _cumulative_dimension(previous_tones, dim)
    current = _cumulative_dimension(tones, dim)

    if current == 0 or previous == 0:
        return tones

    scale_factor = (previous / FEIGENBAUM_RATIO) / current
    return scale_transform(tones, dim, scale_factor)


def phrase_feigenbaum_grow(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-feigenbaum-grow: no preceding phrases exist to relate to.")

    dim = parse_dimension(dimension)
    previous = _cumulative_dimension(previous_tones, dim)
    current = _cumulative_dimension(tones, dim)

    if current == 0 or previous == 0:
        return tones

    scale_factor = (previous * FEIGENBAUM_RATIO) / current
    return scale_transform(tones, dim, scale_factor)


def score_feigenbaum_sequence(score: Score, dimension: ToneDimension | str = ToneDimension.DURATION) -> Score:
    if not score.voices:
        return score

    if len(score.voices) < 2:
        raise ValueError("score_feigenbaum_sequence requires at least 2 voices to apply a sequence.")

    dim = parse_dimension(dimension)
    new_voices = []
    for i, voice in enumerate(score.voices):
        scale_factor = 1.0 / (FEIGENBAUM_RATIO ** i)
        new_tones = scale_transform(voice.tones, dim, scale_factor)
        new_voices.append(Voice(new_tones))

    return Score(new_voices)
