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
class TerracedDriftParams:
    dimension: ToneDimension
    max_step_change_pct: int


def _create_terraced_drift_params(parsed_params: ParsedTransformParams) -> TerracedDriftParams:
    return TerracedDriftParams(
        dimension=parsed_params.required("dimension", ToneDimension),
        max_step_change_pct=parsed_params.required("max_step_change_pct", int),
    )


TERRACED_DRIFT_PARAMS_SPEC = TransformParamsSpec[TerracedDriftParams](
    params_factory=_create_terraced_drift_params,
    fields={
        "dimension": TransformParamFieldSpec(
            required=True,
            schema=ToneDimensionParam(),
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
    tones: list[Tone],
    dimension: ToneDimension,
    max_step_change_pct: int,
) -> list[Tone]:
    if max_step_change_pct < 1 or max_step_change_pct > 100:
        raise ValueError(f"max_step_change_pct must be between 1 and 100, got {max_step_change_pct}")

    step_size = max_step_change_pct / 100.0
    fluctuations = _build_terraced_fluctuations(len(tones), step_size, step_size)
    return apply_fluctuations(tones, fluctuations, dimension, step_size)


def terraced_drift_phrase_transform(context: PhraseTransformContext, params: TerracedDriftParams) -> Phrase:
    phrase_tones = flatten_phrase_tones(context.phrase)
    transformed_tones = apply_terraced_drift_transform(
        phrase_tones,
        dimension=params.dimension,
        max_step_change_pct=params.max_step_change_pct,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])


def terraced_drift_score_transform(score: Score, params: TerracedDriftParams) -> Score:
    new_voices = []
    for voice in score.voices:
        voice_tones = flatten_voice_tones(voice)
        transformed_tones = apply_terraced_drift_transform(
            voice_tones,
            dimension=params.dimension,
            max_step_change_pct=params.max_step_change_pct,
        )
        new_voices.append(Voice(phrases=[Phrase(motifs=[Motif(name="<each_voice>", tones=transformed_tones)])]))

    return Score(voices=new_voices)
