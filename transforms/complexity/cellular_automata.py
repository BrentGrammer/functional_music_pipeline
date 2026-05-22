from collections.abc import Mapping
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms._modulation import apply_fluctuations
from transforms.base import (
    FloatParam,
    IntegerParam,
    PhraseTransformContext,
    ToneDimension,
    ToneDimensionParam,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)


@dataclass(frozen=True)
class CellularAutomataParams:
    dimension: ToneDimension
    rule: int
    generations: int
    max_deviation: float


def _create_cellular_automata_params(parsed_params: Mapping[str, object]) -> CellularAutomataParams:
    dimension = parsed_params.get("dimension")
    rule = parsed_params.get("rule")
    generations = parsed_params.get("generations")
    max_deviation = parsed_params.get("max_deviation")
    if (
        not isinstance(dimension, ToneDimension)
        or not isinstance(rule, int)
        or not isinstance(generations, int)
        or not isinstance(max_deviation, float)
    ):
        raise ValueError("Cellular automata params were not parsed before construction.")

    return CellularAutomataParams(
        dimension=dimension,
        rule=rule,
        generations=generations,
        max_deviation=max_deviation,
    )


CELLULAR_AUTOMATA_PARAMS_SPEC = TransformParamsSpec[CellularAutomataParams](
    params_factory=_create_cellular_automata_params,
    fields={
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            default=ToneDimension.DURATION,
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
    dimension: ToneDimension,
    rule: int,
    generations: int,
    max_deviation: float,
) -> ToneSequence:
    if not tones:
        return []
    if len(tones) == 1:
        return list(tones)

    initial_state = _derive_initial_state(tones, dimension)
    final_state = _evolve_state(initial_state, rule, generations=generations)

    DEAD = -1.0
    LIVE = 1.0
    fluctuations = [DEAD if cell == 0 else LIVE for cell in final_state]

    return apply_fluctuations(tones, fluctuations, dimension, max_deviation)


def cellular_automata_phrase_transform(context: PhraseTransformContext, params: CellularAutomataParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)

    transformed_tones = apply_cellular_automata_transform(
        phrase_tones,
        dimension=params.dimension,
        rule=params.rule,
        generations=params.generations,
        max_deviation=params.max_deviation,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def cellular_automata_score_transform(score: Score, params: CellularAutomataParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        transformed_tones = apply_cellular_automata_transform(
            voice_tones,
            dimension=params.dimension,
            rule=params.rule,
            generations=params.generations,
            max_deviation=params.max_deviation,
        )
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transformed_tones)])]))

    return Score(voices=new_voices)
