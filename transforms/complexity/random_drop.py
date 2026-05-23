import random
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms._modulation import apply_fluctuations
from transforms.base import (
    IntegerParam,
    ParsedTransformParams,
    PhraseTransformContext,
    ToneDimension,
    ToneDimensionParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)


@dataclass(frozen=True)
class RandomDropParams:
    dimension: ToneDimension
    max_drop_pct: int
    drop_frequency_pct: int


def _create_random_drop_params(parsed_params: ParsedTransformParams) -> RandomDropParams:
    return RandomDropParams(
        dimension=parsed_params.required("dimension", ToneDimension),
        max_drop_pct=parsed_params.required("max_drop_pct", int),
        drop_frequency_pct=parsed_params.required("drop_frequency_pct", int),
    )


def _validate_drop_params(max_drop_pct: int, drop_frequency_pct: int) -> None:
    if max_drop_pct < 1 or max_drop_pct > 100:
        raise ValueError(f"max_drop_pct must be between 1 and 100, got {max_drop_pct}")
    if drop_frequency_pct < 1 or drop_frequency_pct > 100:
        raise ValueError(f"drop_frequency_pct must be between 1 and 100, got {drop_frequency_pct}")


RANDOM_DROP_PARAMS_SPEC = TransformParamsSpec[RandomDropParams](
    params_factory=_create_random_drop_params,
    fields={
        "dimension": TransformParamFieldSpec(
            schema=ToneDimensionParam(),
            default=ToneDimension.DURATION,
        ),
        "max_drop_pct": TransformParamFieldSpec(
            required=True,
            schema=IntegerParam(),
        ),
        "drop_frequency_pct": TransformParamFieldSpec(
            required=True,
            schema=IntegerParam(),
        ),
    }
)


def apply_random_drop_transform(
    tones: list[Tone],
    dimension: ToneDimension,
    max_drop_pct: int,
    drop_frequency_pct: int,
) -> list[Tone]:
    _validate_drop_params(max_drop_pct, drop_frequency_pct)
    max_deviation = max_drop_pct / 100.0
    drop_rate = drop_frequency_pct / 100.0

    rng = random.Random(42)
    fluctuations: list[float] = []
    for _ in tones:
        if rng.random() < drop_rate:
            fluctuations.append(-rng.random())
        else:
            fluctuations.append(0.0)

    return apply_fluctuations(tones, fluctuations, dimension, max_deviation)


def random_drop_phrase_transform(context: PhraseTransformContext, params: RandomDropParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)

    transformed_tones = apply_random_drop_transform(
        phrase_tones,
        dimension=params.dimension,
        max_drop_pct=params.max_drop_pct,
        drop_frequency_pct=params.drop_frequency_pct,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def random_drop_score_transform(score: Score, params: RandomDropParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        transformed_tones = apply_random_drop_transform(
            voice_tones,
            dimension=params.dimension,
            max_drop_pct=params.max_drop_pct,
            drop_frequency_pct=params.drop_frequency_pct,
        )
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transformed_tones)])]))

    return Score(voices=new_voices)
