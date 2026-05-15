import random
from dataclasses import dataclass

from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.complexity._modulation import apply_profile

RANDOM_DROP_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "max_deviation": TransformParamFieldSpec(
            required=True,
            schema=FloatParam(),
        ),
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "drop_rate": TransformParamFieldSpec(schema=FloatParam()),
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
    max_deviation: float,
    seed: int = 42,
    drop_rate: float = 0.2,
) -> ToneSequence:
    return apply_profile(
        tones,
        _RandomDropProfile(seed=seed, drop_rate=drop_rate),
        dimension,
        max_deviation,
    )
