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
from transforms.geological._modulation import apply_profile


TERRACED_DRIFT_PARAMS_SPEC = TransformParamsSpec(
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
        "step_size": TransformParamFieldSpec(schema=FloatParam()),
        "quantize_resolution": TransformParamFieldSpec(schema=FloatParam()),
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
    max_deviation: float,
    seed: int = 42,
    step_size: float = 0.25,
    quantize_resolution: float = 0.2,
) -> ToneSequence:
    return apply_profile(
        tones,
        _TerracedBrownianProfile(
            seed=seed,
            step_size=step_size,
            quantize_resolution=quantize_resolution,
        ),
        dimension,
        max_deviation,
    )
