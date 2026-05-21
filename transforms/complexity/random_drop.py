import random
from collections.abc import Mapping

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms._modulation import apply_fluctuations
from transforms.base import (
    EnumParam,
    IntegerParam,
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)


def _validate_drop_params(max_drop_pct: int, drop_frequency_pct: int) -> None:
    if not isinstance(max_drop_pct, int):
        raise ValueError(f"max_drop_pct must be an integer, got {type(max_drop_pct).__name__}")
    if not isinstance(drop_frequency_pct, int):
        raise ValueError(f"drop_frequency_pct must be an integer, got {type(drop_frequency_pct).__name__}")
    if max_drop_pct < 1 or max_drop_pct > 100:
        raise ValueError(f"max_drop_pct must be between 1 and 100, got {max_drop_pct}")
    if drop_frequency_pct < 1 or drop_frequency_pct > 100:
        raise ValueError(f"drop_frequency_pct must be between 1 and 100, got {drop_frequency_pct}")


RANDOM_DROP_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
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
    tones: ToneSequence,
    dimension: ToneDimension,
    max_drop_pct: int,
    drop_frequency_pct: int,
) -> ToneSequence:
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


def random_drop_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)

    dimension = params.get("dimension", ToneDimension.DURATION)
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Random drop dimension must be a string or ToneDimension.")

    max_drop_pct = params["max_drop_pct"]
    if not isinstance(max_drop_pct, int) or isinstance(max_drop_pct, bool):
        raise ValueError("Random drop max_drop_pct must be an integer.")

    drop_frequency_pct = params["drop_frequency_pct"]
    if not isinstance(drop_frequency_pct, int) or isinstance(drop_frequency_pct, bool):
        raise ValueError("Random drop drop_frequency_pct must be an integer.")

    transformed_tones = apply_random_drop_transform(
        phrase_tones,
        dimension=parse_dimension(dimension),
        max_drop_pct=max_drop_pct,
        drop_frequency_pct=drop_frequency_pct,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def random_drop_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    dimension = params.get("dimension", ToneDimension.DURATION)
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Random drop dimension must be a string or ToneDimension.")

    max_drop_pct = params["max_drop_pct"]
    if not isinstance(max_drop_pct, int) or isinstance(max_drop_pct, bool):
        raise ValueError("Random drop max_drop_pct must be an integer.")

    drop_frequency_pct = params["drop_frequency_pct"]
    if not isinstance(drop_frequency_pct, int) or isinstance(drop_frequency_pct, bool):
        raise ValueError("Random drop drop_frequency_pct must be an integer.")

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        resolved_dimension = parse_dimension(dimension)
        transformed_tones = apply_random_drop_transform(
            voice_tones,
            dimension=resolved_dimension,
            max_drop_pct=max_drop_pct,
            drop_frequency_pct=drop_frequency_pct,
        )
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transformed_tones)])]))

    return Score(voices=new_voices)
