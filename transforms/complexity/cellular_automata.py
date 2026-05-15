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

CELLULAR_AUTOMATA_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "max_deviation": TransformParamFieldSpec(
            required=True,
            schema=FloatParam(),
        ),
        "rule": TransformParamFieldSpec(schema=IntegerParam()),
        "seed": TransformParamFieldSpec(schema=IntegerParam()),
        "width": TransformParamFieldSpec(schema=IntegerParam()),
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


@dataclass(frozen=True)
class _CellularAutomataProfile:
    rule: int = 30
    seed: int = 42
    width: int = 31

    def generate(self, length: int) -> list[float]:
        rng = random.Random(self.seed)
        state = [rng.choice([0, 1]) for _ in range(self.width)]
        profile = []
        center_idx = self.width // 2

        for _ in range(length):
            profile.append(-1.0 if state[center_idx] == 0 else 1.0)
            state = _get_next_cellular_state(state, self.rule)

        return profile


def apply_cellular_automata_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    max_deviation: float,
    rule: int = 30,
    seed: int = 42,
    width: int = 31,
) -> ToneSequence:
    return apply_profile(
        tones,
        _CellularAutomataProfile(rule=rule, seed=seed, width=width),
        dimension,
        max_deviation,
    )
