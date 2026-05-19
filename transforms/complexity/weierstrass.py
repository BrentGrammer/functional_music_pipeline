import math
import random
from collections.abc import Mapping
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_phrase_tones, flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    EnumParam,
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.complexity._modulation import apply_profile

_WEIERSTRASS_INTENSITY_PRESETS = {
    "low": {"max_deviation": 0.05, "amplitude_scaling": 0.3, "ripples_per_wave": 2.0, "iterations": 6},
    "medium": {"max_deviation": 0.15, "amplitude_scaling": 0.5, "ripples_per_wave": 3.0, "iterations": 10},
    "high": {"max_deviation": 0.25, "amplitude_scaling": 0.6, "ripples_per_wave": 4.0, "iterations": 12},
    "extreme": {"max_deviation": 0.4, "amplitude_scaling": 0.8, "ripples_per_wave": 6.0, "iterations": 18},
}


def _resolve_intensity(value: str) -> dict:
    if not isinstance(value, str):
        raise ValueError(f"Intensity must be a string, got {type(value).__name__}")
    if value not in _WEIERSTRASS_INTENSITY_PRESETS:
        raise ValueError(
            f"Invalid intensity '{value}'. Must be one of: {', '.join(_WEIERSTRASS_INTENSITY_PRESETS.keys())}"
        )
    return _WEIERSTRASS_INTENSITY_PRESETS[value]


WEIERSTRASS_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "intensity": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(_WEIERSTRASS_INTENSITY_PRESETS.keys())),
        ),
    }
)


@dataclass(frozen=True)
class _WeierstrassProfile:
    seed: int = 42
    amplitude_scaling: float = 0.5
    ripples_per_wave: float = 3.0
    iterations: int = 10

    def generate(self, length: int) -> list[float]:
        random.seed(self.seed)
        start_x = random.uniform(0.0, 100.0)
        step = 0.15

        max_val = sum(self.amplitude_scaling**n for n in range(self.iterations))
        if max_val == 0:
            max_val = 1.0

        profile = []
        for i in range(length):
            x = start_x + (i * step)
            val = 0.0
            for n in range(self.iterations):
                val += (self.amplitude_scaling**n) * math.cos((self.ripples_per_wave**n) * math.pi * x)
            profile.append(val / max_val)

        return profile


def apply_weierstrass_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    intensity: str,
) -> ToneSequence:
    preset = _resolve_intensity(intensity)
    return apply_profile(
        tones,
        _WeierstrassProfile(
            seed=42,
            amplitude_scaling=preset["amplitude_scaling"],
            ripples_per_wave=preset["ripples_per_wave"],
            iterations=preset["iterations"],
        ),
        dimension,
        preset["max_deviation"],
    )


def weierstrass_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension")
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Weierstrass dimension must be a string or ToneDimension.")

    intensity = params.get("intensity")
    if not isinstance(intensity, str):
        raise ValueError("Weierstrass intensity must be a string.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = apply_weierstrass_transform(phrase_tones, dimension=dimension, intensity=intensity)
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def weierstrass_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    dimension = params["dimension"]
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Weierstrass dimension must be a string or ToneDimension.")

    intensity = params["intensity"]
    if not isinstance(intensity, str):
        raise ValueError("Weierstrass intensity must be a string.")

    return Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="<each_voice>",
                                tones=apply_weierstrass_transform(
                                    flatten_voice_tones(voice),
                                    dimension=dimension,
                                    intensity=intensity,
                                ),
                            )
                        ]
                    )
                ]
            )
            for voice in score.voices
        ]
    )
