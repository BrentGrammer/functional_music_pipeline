from collections.abc import Mapping

import random
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from transforms.base import (
    EnumParam,
    IntegerParam,
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.complexity._modulation import apply_profile


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


@dataclass(frozen=True)
class _RandomDropProfile:
    seed: int = 42
    drop_rate: float = 0.2

    def generate(self, length: int) -> list[float]:
        rng = random.Random(self.seed)
        profile = []
        for _ in range(length):
            if rng.random() < self.drop_rate:
                profile.append(-rng.random())
            else:
                profile.append(0.0)
        return profile


def apply_random_drop_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    max_drop_pct: int,
    drop_frequency_pct: int,
) -> ToneSequence:
    _validate_drop_params(max_drop_pct, drop_frequency_pct)
    max_deviation = max_drop_pct / 100.0
    drop_rate = drop_frequency_pct / 100.0
    return apply_profile(
        tones,
        _RandomDropProfile(seed=42, drop_rate=drop_rate),
        dimension,
        max_deviation,
    )


def random_drop_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]

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
        dimension=dimension,
        max_drop_pct=max_drop_pct,
        drop_frequency_pct=drop_frequency_pct,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
