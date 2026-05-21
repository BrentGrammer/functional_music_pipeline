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
)

TERRACED_DRIFT_PARAMS_SPEC = TransformParamsSpec(
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=EnumParam(allowed_values=tuple(ToneDimension)),
        ),
        "max_step_change_pct": TransformParamFieldSpec(
            required=True,
            schema=IntegerParam(),
        ),
    }
)


def _build_terraced_fluctuations(length: int, step_size: float, quantize_resolution: float) -> list[float]:
    random.seed(42)
    current_value = 0.0
    fluctuations: list[float] = []

    for _ in range(length):
        current_value += random.uniform(-step_size, step_size)
        current_value = max(-1.0, min(1.0, current_value))

        if quantize_resolution > 0:
            quantized = round(current_value / quantize_resolution) * quantize_resolution
        else:
            quantized = current_value

        quantized = max(-1.0, min(1.0, quantized))
        fluctuations.append(quantized)

    return fluctuations


def apply_terraced_drift_transform(
    tones: ToneSequence,
    dimension: ToneDimension | str,
    max_step_change_pct: int,
) -> ToneSequence:
    if not isinstance(max_step_change_pct, int):
        raise ValueError(f"max_step_change_pct must be an integer, got {type(max_step_change_pct).__name__}")
    if max_step_change_pct < 1 or max_step_change_pct > 100:
        raise ValueError(f"max_step_change_pct must be between 1 and 100, got {max_step_change_pct}")

    step_size = max_step_change_pct / 100.0
    fluctuations = _build_terraced_fluctuations(len(tones), step_size, step_size)
    return apply_fluctuations(tones, fluctuations, dimension, step_size)


def terraced_drift_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension")
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Terraced drift dimension must be a string or ToneDimension.")

    max_step_change_pct = params.get("max_step_change_pct")
    if not isinstance(max_step_change_pct, int) or isinstance(max_step_change_pct, bool):
        raise ValueError("Terraced drift max_step_change_pct must be an integer.")

    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = apply_terraced_drift_transform(
        phrase_tones,
        dimension=dimension,
        max_step_change_pct=max_step_change_pct,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def terraced_drift_score_transform(score: Score, params: Mapping[str, object]) -> Score:
    dimension = params["dimension"]
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Terraced drift dimension must be a string or ToneDimension.")

    max_step_change_pct = params["max_step_change_pct"]
    if not isinstance(max_step_change_pct, int) or isinstance(max_step_change_pct, bool):
        raise ValueError("Terraced drift max_step_change_pct must be an integer.")

    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        transformed_tones = apply_terraced_drift_transform(
            voice_tones,
            dimension=dimension,
            max_step_change_pct=max_step_change_pct,
        )
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transformed_tones)])]))

    return Score(voices=new_voices)
