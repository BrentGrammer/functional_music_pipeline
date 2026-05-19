from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)
from transforms.complexity._modulation import _modulate_tone_dimension

CELLULAR_AUTOMATA_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "rule": TransformParamFieldSpec(
            required=True,
            schema=IntegerParam(),
        ),
        "generations": TransformParamFieldSpec(
            required=True,
            schema=IntegerParam(),
        ),
        "max_deviation": TransformParamFieldSpec(
            required=True,
            schema=FloatParam(),
        ),
    }
)


def _get_next_cellular_state(state: list[int], rule: int) -> list[int]:
    next_state = [0] * len(state)

    for index in range(len(state)):
        left = state[(index - 1) % len(state)]
        center = state[index]
        right = state[(index + 1) % len(state)]
        neighborhood = (left << 2) | (center << 1) | right
        next_state[index] = (rule >> neighborhood) & 1

    return next_state


def _derive_initial_state(tones: ToneSequence, dimension: ToneDimension) -> list[int]:
    """
    Converts the input tones into a binary starting row for the cellular automaton.

    Extracts the target dimension value (frequency, duration, or amplitude) from each
    tone, then splits them into two groups — above and below the median — producing a
    1 or 0 per tone. This binary row becomes the CA's initial state, one cell per tone.

    The result is that the music's own structure seeds the automaton: two pieces with
    different pitch contours will produce different evolutions under the same rule.
    """
    if dimension == ToneDimension.FREQUENCY:
        values = [tone.frequency for tone in tones]
    elif dimension == ToneDimension.DURATION:
        values = [tone.duration for tone in tones]
    elif dimension == ToneDimension.AMPLITUDE:
        values = [tone.amplitude for tone in tones]
    else:
        raise ValueError("Tone Dimension invalid")

    if min(values) == max(values):
        # All tones have the same value in this dimension — there's no variation to
        # threshold into a binary pattern. Rather than giving the CA a flat all-0 or
        # all-1 starting row (which would produce a trivial, uninteresting evolution),
        # we fall back to an alternating [1, 0, 1, 0, ...] pattern. This gives the
        # rule a non-trivial structure to evolve from.
        return [i % 2 for i in range(len(values))]

    median = sorted(values)[len(values) // 2]
    return [1 if v >= median else 0 for v in values]


def _evolve_state(state: list[int], rule: int, generations: int) -> list[int]:
    for _ in range(generations):
        state = _get_next_cellular_state(state, rule)
    return state


def apply_cellular_automata_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    rule: int,
    generations: int,
    max_deviation: float,
) -> ToneSequence:
    if not tones:
        return []
    if len(tones) == 1:
        return list(tones)

    resolved_dimension = parse_dimension(dimension)

    initial_state = _derive_initial_state(tones, resolved_dimension)
    final_state = _evolve_state(initial_state, rule, generations=generations)

    # Translate the evolved binary state into modulation values.
    # Dead cells (0) pull the tone down (-1.0), live cells (1) push it up (+1.0).
    # _modulate_tone_dimension then scales these by max_deviation to control
    # how strongly the pattern affects the music.
    DEAD = -1.0
    LIVE = 1.0
    profile = [DEAD if cell == 0 else LIVE for cell in final_state]

    return _modulate_tone_dimension(tones, profile, resolved_dimension, max_deviation)


def cellular_automata_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]

    dimension = params.get("dimension", ToneDimension.DURATION)
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Cellular automata dimension must be a string or ToneDimension.")

    rule = params["rule"]
    if not isinstance(rule, int) or isinstance(rule, bool):
        raise ValueError("Cellular automata rule must be an integer.")

    generations = params["generations"]
    if not isinstance(generations, int) or isinstance(generations, bool):
        raise ValueError("Cellular automata generations must be an integer.")

    max_deviation = params["max_deviation"]
    if not isinstance(max_deviation, (int, float)) or isinstance(max_deviation, bool):
        raise ValueError("Cellular automata max_deviation must be a float.")

    transformed_tones = apply_cellular_automata_transform(
        phrase_tones,
        dimension=dimension,
        rule=rule,
        generations=generations,
        max_deviation=float(max_deviation),
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
