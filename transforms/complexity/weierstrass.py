import math
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
    PhraseTransformContext,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)

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


def _build_weierstrass_fluctuations(
    length: int, amplitude_scaling: float, ripples_per_wave: float, iterations: int
) -> list[float]:
    random.seed(42)
    start_x = random.uniform(0.0, 100.0)
    step = 0.15

    max_val = sum(amplitude_scaling**n for n in range(iterations))
    if max_val == 0:
        max_val = 1.0

    fluctuations: list[float] = []
    for i in range(length):
        x = start_x + (i * step)
        val = 0.0
        for n in range(iterations):
            val += (amplitude_scaling**n) * math.cos((ripples_per_wave**n) * math.pi * x)
        fluctuations.append(val / max_val)

    return fluctuations


def apply_weierstrass_transform(
    tones: ToneSequence,
    dimension: ToneDimension,
    intensity: str,
) -> ToneSequence:
    preset = _resolve_intensity(intensity)
    fluctuations = _build_weierstrass_fluctuations(
        len(tones),
        preset["amplitude_scaling"],
        preset["ripples_per_wave"],
        preset["iterations"],
    )
    return apply_fluctuations(tones, fluctuations, dimension, preset["max_deviation"])


def weierstrass_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension")
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Weierstrass dimension must be a string or ToneDimension.")

    intensity = params.get("intensity")
    if not isinstance(intensity, str):
        raise ValueError("Weierstrass intensity must be a string.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = apply_weierstrass_transform(
        phrase_tones, dimension=dimension, intensity=intensity
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def weierstrass_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    dimension = params["dimension"]
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Weierstrass dimension must be a string or ToneDimension.")

    intensity = params["intensity"]
    if not isinstance(intensity, str):
        raise ValueError("Weierstrass intensity must be a string.")

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        transformed_tones = apply_weierstrass_transform(
            voice_tones,
            dimension=dimension,
            intensity=intensity,
        )
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transformed_tones)])]))

    return Score(voices=new_voices)
