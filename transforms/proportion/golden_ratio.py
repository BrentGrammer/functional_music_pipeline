from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.math_constants import GOLDEN_RATIO
from transforms.base import (
    EnumParam,
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)
from transforms.basic.scale import scale_transform

GOLDEN_RATIO_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
    }
)


def _cumulative_dimension(tones: ToneSequence, dim: ToneDimension) -> float:
    dimension = dim.value
    return float(sum(getattr(t, dimension) for t in tones))


def golden_ratio_transform(tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION) -> ToneSequence:
    return scale_transform(tones, dimension, 1 / GOLDEN_RATIO)


def golden_ratio_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension", ToneDimension.DURATION)
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Golden ratio dimension must be a string or ToneDimension.")

    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    transformed_tones = golden_ratio_transform(phrase_tones, dimension=dimension)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def phrase_golden_ratio_shrink(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-golden-ratio-shrink: no preceding phrases exist to relate to.")

    dim = parse_dimension(dimension)
    prev_val = _cumulative_dimension(previous_tones, dim)
    curr_val = _cumulative_dimension(tones, dim)

    if curr_val == 0 or prev_val == 0:
        return tones

    scale_factor = (prev_val / GOLDEN_RATIO) / curr_val
    return scale_transform(tones, dim, scale_factor)


def phrase_golden_ratio_grow(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-golden-ratio-grow: no preceding phrases exist to relate to.")

    dim = parse_dimension(dimension)
    prev_val = _cumulative_dimension(previous_tones, dim)
    curr_val = _cumulative_dimension(tones, dim)

    if curr_val == 0 or prev_val == 0:
        return tones

    scale_factor = (prev_val * GOLDEN_RATIO) / curr_val
    return scale_transform(tones, dim, scale_factor)
