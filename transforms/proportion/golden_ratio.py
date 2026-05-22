from dataclasses import dataclass

from score_model.math_constants import GOLDEN_RATIO
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    ParsedTransformParams,
    PhraseTransformContext,
    ToneDimension,
    ToneDimensionParam,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.basic.scale import scale_transform


@dataclass(frozen=True)
class GoldenRatioParams:
    dimension: ToneDimension


def _golden_ratio_params_factory(parsed: ParsedTransformParams) -> GoldenRatioParams:
    return GoldenRatioParams(dimension=parsed.required("dimension", ToneDimension))


GOLDEN_RATIO_PARAMS_SPEC = TransformParamsSpec[GoldenRatioParams](
    fields={
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            default=ToneDimension.DURATION,
        ),
    },
    params_factory=_golden_ratio_params_factory,
)


def _cumulative_dimension(tones: ToneSequence, dim: ToneDimension) -> float:
    dimension = dim.value
    return float(sum(getattr(t, dimension) for t in tones))


def golden_ratio_transform(tones: ToneSequence, dimension: ToneDimension = ToneDimension.DURATION) -> ToneSequence:
    return scale_transform(tones, dimension, 1 / GOLDEN_RATIO)


def _previous_phrase_tones(context: PhraseTransformContext) -> list:
    if context.phrase_index > 0:
        return [
            tone
            for phrase in context.score.voices[context.voice_index].phrases[:context.phrase_index]
            for motif in phrase.motifs
            for tone in motif.tones
        ]
    if context.voice_index > 0:
        return flatten_voice_tones(context.score.voices[context.voice_index - 1])
    return []


def golden_ratio_phrase_transform(context: PhraseTransformContext, params: GoldenRatioParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = golden_ratio_transform(phrase_tones, dimension=params.dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def phrase_golden_ratio_shrink_transform(
    context: PhraseTransformContext,
    params: GoldenRatioParams,
) -> Phrase:
    current_tones = flatten_phrase_tones(context.phrase)
    previous_tones = _previous_phrase_tones(context)

    result = phrase_golden_ratio_shrink(current_tones, previous_tones, dimension=params.dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=result)])


def phrase_golden_ratio_grow_transform(
    context: PhraseTransformContext,
    params: GoldenRatioParams,
) -> Phrase:
    current_tones = flatten_phrase_tones(context.phrase)
    previous_tones = _previous_phrase_tones(context)

    result = phrase_golden_ratio_grow(current_tones, previous_tones, dimension=params.dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=result)])


def phrase_golden_ratio_shrink(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-golden-ratio-shrink: no preceding phrases exist to relate to.")

    prev_val = _cumulative_dimension(previous_tones, dimension)
    curr_val = _cumulative_dimension(tones, dimension)

    if curr_val == 0 or prev_val == 0:
        return tones

    scale_factor = (prev_val / GOLDEN_RATIO) / curr_val
    return scale_transform(tones, dimension, scale_factor)


def phrase_golden_ratio_grow(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-golden-ratio-grow: no preceding phrases exist to relate to.")

    prev_val = _cumulative_dimension(previous_tones, dimension)
    curr_val = _cumulative_dimension(tones, dimension)

    if curr_val == 0 or prev_val == 0:
        return tones

    scale_factor = (prev_val * GOLDEN_RATIO) / curr_val
    return scale_transform(tones, dimension, scale_factor)


def golden_ratio_score_transform(score: Score, params: GoldenRatioParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        transformed_tones = golden_ratio_transform(voice_tones, dimension=params.dimension)
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transformed_tones)])]))

    return Score(voices=new_voices)
