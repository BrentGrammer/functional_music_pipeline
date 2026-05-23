from dataclasses import dataclass

from score_model.math_constants import FEIGENBAUM_DELTA as FEIGENBAUM_RATIO
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones, previous_phrase_tones
from score_model.voice import Voice
from transforms.base import (
    ParsedTransformParams,
    PhraseTransformContext,
    ToneDimension,
    ToneDimensionParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.basic.scale import scale_transform


@dataclass(frozen=True)
class FeigenbaumParams:
    dimension: ToneDimension


def _feigenbaum_params_factory(parsed: ParsedTransformParams) -> FeigenbaumParams:
    return FeigenbaumParams(dimension=parsed.required("dimension", ToneDimension))


FEIGENBAUM_PARAMS_SPEC = TransformParamsSpec[FeigenbaumParams](
    fields={
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            default=ToneDimension.DURATION,
        ),
    },
    params_factory=_feigenbaum_params_factory,
)


def _cumulative_dimension(tones: list[Tone], dim: ToneDimension) -> float:
    dimension = dim.value
    return float(sum(getattr(t, dimension) for t in tones))


def feigenbaum_sequence(tones: list[Tone], dimension: ToneDimension = ToneDimension.DURATION) -> list[Tone]:
    if not tones:
        return []

    dim_attr = dimension.name.lower()
    new_tones = [tones[0]]

    for tone in tones[1:]:
        previous = getattr(new_tones[-1], dim_attr)
        new_val = previous / FEIGENBAUM_RATIO

        freq = tone.frequency
        dur = tone.duration
        amp = tone.amplitude

        if dimension == ToneDimension.FREQUENCY:
            freq = max(1.0, new_val)
        elif dimension == ToneDimension.DURATION:
            dur = max(0.0, new_val)
        elif dimension == ToneDimension.AMPLITUDE:
            amp = max(0.0, min(1.0, new_val))

        new_tones.append(Tone(frequency=freq, duration=dur, sample_rate=tone.sample_rate, amplitude=amp))

    return new_tones

def feigenbaum_sequence_phrase_transform(context: PhraseTransformContext, params: FeigenbaumParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = feigenbaum_sequence(phrase_tones, dimension=params.dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def phrase_feigenbaum_shrink(
    tones: list[Tone], previous_tones: list[Tone], dimension: ToneDimension = ToneDimension.DURATION
) -> list[Tone]:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-feigenbaum-shrink: no preceding phrases exist to relate to.")

    previous = _cumulative_dimension(previous_tones, dimension)
    current = _cumulative_dimension(tones, dimension)

    if current == 0 or previous == 0:
        return tones

    scale_factor = (previous / FEIGENBAUM_RATIO) / current
    return scale_transform(tones, dimension, scale_factor)


def phrase_feigenbaum_shrink_transform(
    context: PhraseTransformContext,
    params: FeigenbaumParams,
) -> Phrase:
    current_tones = flatten_phrase_tones(context.phrase)
    previous_tones = previous_phrase_tones(context.score, context.voice_index, context.phrase_index)

    result = phrase_feigenbaum_shrink(current_tones, previous_tones, dimension=params.dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=result)])


def phrase_feigenbaum_grow_transform(
    context: PhraseTransformContext,
    params: FeigenbaumParams,
) -> Phrase:
    current_tones = flatten_phrase_tones(context.phrase)
    previous_tones = previous_phrase_tones(context.score, context.voice_index, context.phrase_index)

    result = phrase_feigenbaum_grow(current_tones, previous_tones, dimension=params.dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=result)])


def phrase_feigenbaum_grow(
    tones: list[Tone], previous_tones: list[Tone], dimension: ToneDimension = ToneDimension.DURATION
) -> list[Tone]:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-feigenbaum-grow: no preceding phrases exist to relate to.")

    previous = _cumulative_dimension(previous_tones, dimension)
    current = _cumulative_dimension(tones, dimension)

    if current == 0 or previous == 0:
        return tones

    scale_factor = (previous * FEIGENBAUM_RATIO) / current
    return scale_transform(tones, dimension, scale_factor)


def score_feigenbaum_sequence(score: Score, dimension: ToneDimension = ToneDimension.DURATION) -> Score:
    if not score.voices:
        return score

    if len(score.voices) < 2:
        raise ValueError("score_feigenbaum_sequence requires at least 2 voices to apply a sequence.")

    new_voices = []
    for i, voice in enumerate(score.voices):
        scale_factor = 1.0 / (FEIGENBAUM_RATIO ** i)
        new_tones = scale_transform(flatten_voice_tones(voice), dimension, scale_factor)
        new_voices.append(
            Voice(phrases=[Phrase(motifs=[Motif(name="<feigenbaum>", tones=new_tones)])])
        )

    return Score(new_voices)


def feigenbaum_sequence_score_transform(score: Score, params: FeigenbaumParams) -> Score:
    return score_feigenbaum_sequence(score, dimension=params.dimension)
