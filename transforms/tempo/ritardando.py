import random
from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.traversal import flatten_phrase_tones
from transforms.base import PhraseTransformContext, ToneSequence
from transforms.tempo._common import (
    apply_duration_multipliers,
    build_tempo_change_params_spec,
    compute_jaggedness_weights,
    compute_tempo_change_factors,
    resolve_jaggedness,
    resolve_strength,
)

RITARDANDO_PARAMS_SPEC = build_tempo_change_params_spec()

_INTERNAL_RANDOM = random.Random(42)


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


def ritardando_transform(
    tones: ToneSequence,
    strength: str | float = "medium",
    jaggedness: str | float = "none",
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

    final_duration_multiplier = _resolve_ritardando_final_duration_multiplier(resolved_strength)
    trend_multipliers = compute_tempo_change_factors(len(tones), 1.0, final_duration_multiplier)
    jaggedness_weights = compute_jaggedness_weights(len(tones), resolved_jaggedness, _INTERNAL_RANDOM)

    combined_multipliers = [
        trend * weight for trend, weight in zip(trend_multipliers, jaggedness_weights)
    ]

    return apply_duration_multipliers(tones, combined_multipliers)


def ritardando_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    strength = params.get("strength", "medium")
    if isinstance(strength, bool) or not isinstance(strength, (str, float)):
        raise ValueError("Param 'strength' must be a string or float.")

    jaggedness = params.get("jaggedness", "none")
    if isinstance(jaggedness, bool) or not isinstance(jaggedness, (str, float)):
        raise ValueError("Param 'jaggedness' must be a string or float.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = ritardando_transform(phrase_tones, strength=strength, jaggedness=jaggedness)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
