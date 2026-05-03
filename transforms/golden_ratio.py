from score_model.math_constants import GOLDEN_RATIO
from transforms.base import ToneDimension, ToneSequence, parse_dimension
from transforms.scale import scale_transform


def _get_total(tones: ToneSequence, dim: ToneDimension) -> float:
    attr = dim.name.lower()
    return sum(getattr(t, attr) for t in tones)


def golden_ratio_transform(tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION) -> ToneSequence:
    return scale_transform(tones, dimension, 1 / GOLDEN_RATIO)


def phrase_golden_ratio_shrink(
    tones: ToneSequence, previous_tones: ToneSequence, dimension: ToneDimension | str = ToneDimension.DURATION
) -> ToneSequence:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-golden-ratio-shrink: no preceding phrases exist to relate to.")

    dim = parse_dimension(dimension)
    prev_val = _get_total(previous_tones, dim)
    curr_val = _get_total(tones, dim)

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
    prev_val = _get_total(previous_tones, dim)
    curr_val = _get_total(tones, dim)

    if curr_val == 0 or prev_val == 0:
        return tones

    scale_factor = (prev_val * GOLDEN_RATIO) / curr_val
    return scale_transform(tones, dim, scale_factor)
