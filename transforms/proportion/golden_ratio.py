from dataclasses import dataclass

from score_model.math_constants import GOLDEN_RATIO
from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    PhraseTransformContext,
    ToneDimension,
    ToneDimensionParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.basic.scale import scale_transform


@dataclass(frozen=True)
class GoldenRatioParams:
    dimension: ToneDimension


GOLDEN_RATIO_PARAMS_SPEC = TransformParamsSpec[GoldenRatioParams](
    fields={
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            default=ToneDimension.DURATION,
        ),
    },
    params_factory=lambda parsed: GoldenRatioParams(
        dimension=parsed.required("dimension", ToneDimension),
    ),
)


def golden_ratio_transform_shrink(
    tones: list[Tone],
    dimension: ToneDimension = ToneDimension.DURATION,
) -> list[Tone]:
    """Reduce the selected dimension by the golden ratio, to 61.8% of its original value."""
    return scale_transform(tones, dimension, 1 / GOLDEN_RATIO)


def _previous_phrase_tones(context: PhraseTransformContext) -> list[Tone]:
    if context.phrase_index > 0:
        return [
            tone
            for phrase in context.score.voices[context.voice_index].phrases[: context.phrase_index]
            for motif in phrase.motifs
            for tone in motif.tones
        ]

    if context.voice_index > 0:
        return flatten_voice_tones(context.score.voices[context.voice_index - 1])

    return []


def golden_ratio_single_phrase_transform(
    context: PhraseTransformContext,
    params: GoldenRatioParams,
) -> Phrase:
    transformed_tones = golden_ratio_transform_shrink(
        flatten_phrase_tones(context.phrase),
        params.dimension,
    )

    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def phrase_relative_golden_ratio_shrink_transform(
    context: PhraseTransformContext,
    params: GoldenRatioParams,
) -> Phrase:
    transformed_tones = phrase_relative_golden_ratio_shrink(
        flatten_phrase_tones(context.phrase),
        _previous_phrase_tones(context),
        params.dimension,
    )

    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def phrase_relative_golden_ratio_grow_transform(
    context: PhraseTransformContext,
    params: GoldenRatioParams,
) -> Phrase:
    transformed_tones = phrase_relative_golden_ratio_grow(
        flatten_phrase_tones(context.phrase),
        _previous_phrase_tones(context),
        params.dimension,
    )

    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def phrase_relative_golden_ratio_shrink(
    tones: list[Tone],
    previous_tones: list[Tone],
    dimension: ToneDimension = ToneDimension.DURATION,
) -> list[Tone]:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-golden-ratio-shrink: no preceding phrases exist to relate to.")

    prev_val = float(sum(getattr(t, dimension.value) for t in previous_tones))
    curr_val = float(sum(getattr(t, dimension.value) for t in tones))

    if curr_val == 0 or prev_val == 0:
        return tones

    return scale_transform(tones, dimension, (prev_val / GOLDEN_RATIO) / curr_val)


def phrase_relative_golden_ratio_grow(
    tones: list[Tone],
    previous_tones: list[Tone],
    dimension: ToneDimension = ToneDimension.DURATION,
) -> list[Tone]:
    if not tones:
        return tones

    if not previous_tones:
        raise ValueError("Cannot apply phrase-golden-ratio-grow: no preceding phrases exist to relate to.")

    prev_val = float(sum(getattr(t, dimension.value) for t in previous_tones))
    curr_val = float(sum(getattr(t, dimension.value) for t in tones))

    if curr_val == 0 or prev_val == 0:
        return tones

    return scale_transform(tones, dimension, (prev_val * GOLDEN_RATIO) / curr_val)


def golden_ratio_score_transform(score: Score, params: GoldenRatioParams) -> Score:
    new_voices = []

    for voice in score.voices:
        transformed_tones = golden_ratio_transform_shrink(
            flatten_voice_tones(voice),
            params.dimension,
        )

        new_voices.append(
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(name="<each_voice>", tones=transformed_tones),
                        ],
                    ),
                ],
            ),
        )

    return Score(voices=new_voices)