from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
import random

from transforms.base import PhraseTransformContext, ToneSequence
from transforms.tempo._common import (
    apply_duration_multipliers,
    build_tempo_change_params_spec,
    compute_jaggedness_weights,
    compute_tempo_change_factors,
    resolve_jaggedness,
    resolve_strength,
)

ACCELERANDO_PARAMS_SPEC = build_tempo_change_params_spec()

_INTERNAL_RANDOM = random.Random(42)


def _resolve_accelerando_final_duration_multiplier(strength: float) -> float:
    """
    Map public strength (0.0 to 1.0) to the duration multiplier for the final tone.

    At strength=0.0, multiplier=1.0 (no change).
    At strength=1.0, durations shrink to the minimum safe ratio.
    """
    MIN_DURATION_RATIO = 0.10
    NEUTRAL_MULTIPLIER = 1.0
    return NEUTRAL_MULTIPLIER - strength * (NEUTRAL_MULTIPLIER - MIN_DURATION_RATIO)


def accelerando_transform(
    tones: ToneSequence,
    strength: str | float = "medium",
    jaggedness: str | float = "none",
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

    final_duration_multiplier = _resolve_accelerando_final_duration_multiplier(resolved_strength)
    trend_multipliers = compute_tempo_change_factors(len(tones), 1.0, final_duration_multiplier)
    jaggedness_weights = compute_jaggedness_weights(len(tones), resolved_jaggedness, _INTERNAL_RANDOM)

    combined_multipliers = [
        trend * weight for trend, weight in zip(trend_multipliers, jaggedness_weights)
    ]

    return apply_duration_multipliers(tones, combined_multipliers)


def accelerando_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    strength = params.get("strength", "medium")
    if isinstance(strength, bool) or not isinstance(strength, (str, float)):
        raise ValueError("Param 'strength' must be a string or float.")

    jaggedness = params.get("jaggedness", "none")
    if isinstance(jaggedness, bool) or not isinstance(jaggedness, (str, float)):
        raise ValueError("Param 'jaggedness' must be a string or float.")

    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    transformed_tones = accelerando_transform(phrase_tones, strength=strength, jaggedness=jaggedness)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
