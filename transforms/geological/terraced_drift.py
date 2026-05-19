import random
from collections.abc import Mapping
from dataclasses import dataclass

from score_model.motif import Motif
from score_model.phrase import Phrase
from transforms.base import (
    EnumParam,
    PhraseTransformContext,
    IntegerParam,
    ToneDimension,
    ToneSequence,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.geological._modulation import apply_profile

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


@dataclass(frozen=True)
class _TerracedBrownianProfile:
    seed: int = 42
    step_size: float = 0.25
    quantize_resolution: float = 0.2

    def generate(self, length: int) -> list[float]:
        random.seed(self.seed)
        current_value = 0.0
        profile = []

        for _ in range(length):
            current_value += random.uniform(-self.step_size, self.step_size)
            current_value = max(-1.0, min(1.0, current_value))

            if self.quantize_resolution > 0:
                quantized = round(current_value / self.quantize_resolution) * self.quantize_resolution
            else:
                quantized = current_value

            quantized = max(-1.0, min(1.0, quantized))
            profile.append(quantized)

        return profile


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

    return apply_profile(
        tones,
        _TerracedBrownianProfile(
            seed=42,
            step_size=step_size,
            quantize_resolution=step_size,
        ),
        dimension,
        step_size,
    )


def terraced_drift_phrase_transform(context: PhraseTransformContext, params: Mapping[str, object]) -> Phrase:
    dimension = params.get("dimension")
    if not isinstance(dimension, (str, ToneDimension)):
        raise ValueError("Terraced drift dimension must be a string or ToneDimension.")

    max_step_change_pct = params.get("max_step_change_pct")
    if not isinstance(max_step_change_pct, int) or isinstance(max_step_change_pct, bool):
        raise ValueError("Terraced drift max_step_change_pct must be an integer.")

    phrase_tones = [
        tone
        for motif in context.phrase.motifs
        for tone in motif.tones
    ]
    transformed_tones = apply_terraced_drift_transform(
        phrase_tones,
        dimension=dimension,
        max_step_change_pct=max_step_change_pct,
    )
    return Phrase(motifs=[Motif(name="<transformed>", tones=transformed_tones)])
