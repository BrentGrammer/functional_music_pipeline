import random
from dataclasses import dataclass

from score_model.tone import Tone
from transforms.base import (
    EnumParam,
    FloatParam,
    IntegerParam,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
    parse_dimension,
)

_DIMENSION_FIELD = TransformParamFieldSpec(
    required=True,
    schema=EnumParam(allowed_values=tuple(ToneDimension)),
)
_MAX_DEVIATION_FIELD = TransformParamFieldSpec(
    required=True,
    schema=FloatParam(),
)


def _build_params_spec(
    extra_fields: dict[str, TransformParamFieldSpec],
) -> TransformParamsSpec:
    return TransformParamsSpec(
        fields={
            "dimension": _DIMENSION_FIELD,
            "max_deviation": _MAX_DEVIATION_FIELD,
            **extra_fields,
        }
    )


CELLULAR_AUTOMATA_PARAMS_SPEC = _build_params_spec(
    {
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


def _modulate_tone_dimension(
    tones: ToneSequence,
    profile: list[float],
    dimension: ToneDimension,
    max_deviation: float,
) -> ToneSequence:
    result = []
    for tone, value in zip(tones, profile):
        scale = 1.0 + (value * max_deviation)

        if dimension == ToneDimension.FREQUENCY:
            result.append(Tone(max(1.0, tone.frequency * scale), tone.duration, tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.DURATION:
            result.append(Tone(tone.frequency, max(0.001, tone.duration * scale), tone.sample_rate, tone.amplitude))
        elif dimension == ToneDimension.AMPLITUDE:
            result.append(Tone(tone.frequency, tone.duration, tone.sample_rate, max(0.0, min(1.0, tone.amplitude * scale))))

    return result


def _apply_profile(
    tones: ToneSequence,
    profile: _CellularAutomataProfile,
    dimension: ToneDimension | str,
    max_deviation: float,
) -> ToneSequence:
    if not tones:
        return []

    resolved_dimension = parse_dimension(dimension)
    return _modulate_tone_dimension(
        tones,
        profile.generate(len(tones)),
        resolved_dimension,
        max_deviation,
    )


def apply_cellular_automata_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    max_deviation: float,
    rule: int = 30,
    seed: int = 42,
    width: int = 31,
) -> ToneSequence:
    return _apply_profile(
        tones,
        _CellularAutomataProfile(rule=rule, seed=seed, width=width),
        dimension,
        max_deviation,
    )
