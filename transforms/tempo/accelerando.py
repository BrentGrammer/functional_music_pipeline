import random

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones
from transforms.base import PhraseTransformContext
from transforms.tempo._common import (
    TempoChangeParams,
    apply_duration_multipliers,
    build_tempo_change_params_spec,
    compute_jaggedness_weights,
    compute_tempo_change_factors,
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
    tones: list[Tone],
    strength: float,
    jaggedness: float,
) -> list[Tone]:
    """
    Apply an accelerando effect that gradually shortens durations across the phrase.

    Higher strength produces shorter durations toward the end of the phrase.
    Higher jaggedness adds stochastic variation, allowing local duration reversals.
    """
    if not tones:
        return []

    final_duration_multiplier = _resolve_accelerando_final_duration_multiplier(strength)
    trend_multipliers = compute_tempo_change_factors(len(tones), 1.0, final_duration_multiplier)
    jaggedness_weights = compute_jaggedness_weights(len(tones), jaggedness, _INTERNAL_RANDOM)

    combined_multipliers = [
        trend * weight for trend, weight in zip(trend_multipliers, jaggedness_weights)
    ]

    return apply_duration_multipliers(tones, combined_multipliers)


def accelerando_phrase_transform(context: PhraseTransformContext, params: TempoChangeParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = accelerando_transform(phrase_tones, strength=params.strength, jaggedness=params.jaggedness)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
