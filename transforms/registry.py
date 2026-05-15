from composition.transform_params_validation import validate_add_pedal_point_params
from transforms.base import (
    AllVoicesTransform,
    EnumParam,
    FloatParam,
    IntegerParam,
    PhraseRelativeTransform,
    PhraseTransform,
    ScoreTargetMotifsTransform,
    ScoreTransform,
    StringParam,
    ToneDimension,
    TransformParamFieldSpec,
    TransformParamsSpec,
    TransformWithCallable,
)
from transforms.delay import delay_tones
from transforms.drift import drift_transform
from transforms.duration import (
    INTENSITY_LEVELS,
    accelerando_transform,
    feigenbaum_sequence,
    phrase_feigenbaum_grow,
    phrase_feigenbaum_shrink,
    ritardando_transform,
    score_feigenbaum_sequence,
)
from transforms.erosion import erosion_transform
from transforms.frost import frost_effect
from transforms.fugue import NAMED_STRETTO_SPACINGS, add_pedal_point, stretto
from transforms.geological import (
    apply_cellular_automata_transform,
    apply_random_drop_transform,
    apply_ridged_drop_transform,
    apply_terraced_drift_transform,
    apply_weierstrass_transform,
)
from transforms.golden_ratio import (
    golden_ratio_transform,
    phrase_golden_ratio_grow,
    phrase_golden_ratio_shrink,
)
from transforms.inversion import invert_tones
from transforms.pad_silence import pad_silence_tones
from transforms.repeat import repeat_tones
from transforms.reversal import reverse_tones
from transforms.scale import scale_transform
from transforms.transpose import transpose_tones

TRANSFORMS: dict[str, TransformWithCallable] = {
    "reverse": PhraseTransform(
        "reverse",
        reverse_tones,
        params_spec=TransformParamsSpec(),
    ),
    "golden_ratio": PhraseTransform(
        "golden_ratio",
        golden_ratio_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "invert": PhraseTransform(
        "invert",
        invert_tones,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "feigenbaum_sequence": PhraseTransform(
        "feigenbaum_sequence",
        feigenbaum_sequence,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "transpose": PhraseTransform(
        "transpose",
        transpose_tones,
        params_spec=TransformParamsSpec(
            fields={
                "semitones": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                )
            }
        ),
    ),
    "scale": PhraseTransform(
        "scale",
        scale_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "factor": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
            }
        ),
    ),
    "pad_silence": PhraseTransform(
        "pad_silence",
        pad_silence_tones,
        params_spec=TransformParamsSpec(
            fields={
                "seconds": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "position": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=("start", "end")),
                ),
            }
        ),
    ),
    "delay": PhraseTransform(
        "delay",
        delay_tones,
        params_spec=TransformParamsSpec(
            fields={
                "seconds": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                )
            }
        ),
    ),
    "repeat": PhraseTransform(
        "repeat",
        repeat_tones,
        params_spec=TransformParamsSpec(
            fields={
                "count": TransformParamFieldSpec(
                    schema=IntegerParam(),
                    required=True,
                )
            }
        ),
    ),
    "erosion": PhraseTransform(
        "erosion",
        erosion_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "drift": PhraseTransform(
        "drift",
        drift_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "rate": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
            }
        ),
    ),
    "phrase_feigenbaum_shrink": PhraseRelativeTransform(
        "phrase_feigenbaum_shrink",
        phrase_feigenbaum_shrink,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "phrase_feigenbaum_grow": PhraseRelativeTransform(
        "phrase_feigenbaum_grow",
        phrase_feigenbaum_grow,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "phrase_golden_ratio_shrink": PhraseRelativeTransform(
        "phrase_golden_ratio_shrink",
        phrase_golden_ratio_shrink,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "phrase_golden_ratio_grow": PhraseRelativeTransform(
        "phrase_golden_ratio_grow",
        phrase_golden_ratio_grow,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "score_feigenbaum_sequence": ScoreTransform(
        "score_feigenbaum_sequence",
        score_feigenbaum_sequence,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "score_reverse": AllVoicesTransform(
        "score_reverse",
        reverse_tones,
        params_spec=TransformParamsSpec(),
    ),
    "score_golden_ratio": AllVoicesTransform(
        "score_golden_ratio",
        golden_ratio_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "score_invert": AllVoicesTransform(
        "score_invert",
        invert_tones,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
            }
        ),
    ),
    "score_transpose": AllVoicesTransform(
        "score_transpose",
        transpose_tones,
        params_spec=TransformParamsSpec(
            fields={
                "semitones": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                )
            }
        ),
    ),
    "score_scale": AllVoicesTransform(
        "score_scale",
        scale_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "factor": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
            }
        ),
    ),
    "score_delay": AllVoicesTransform(
        "score_delay",
        delay_tones,
        params_spec=TransformParamsSpec(
            fields={
                "seconds": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                )
            }
        ),
    ),
    "score_repeat": AllVoicesTransform(
        "score_repeat",
        repeat_tones,
        params_spec=TransformParamsSpec(
            fields={
                "count": TransformParamFieldSpec(
                    schema=IntegerParam(),
                    required=True,
                )
            }
        ),
    ),
    "score_drift": AllVoicesTransform(
        "score_drift",
        drift_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "rate": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
            }
        ),
    ),
    "add_pedal_point": ScoreTransform(
        "add_pedal_point",
        add_pedal_point,
        params_spec=TransformParamsSpec(
            fields={
                "frequency": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "duration": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "amplitude": TransformParamFieldSpec(
                    schema=FloatParam(),
                ),
                "mode": TransformParamFieldSpec(
                    schema=EnumParam(allowed_values=("sustain", "repeat")),
                ),
                "pulse_duration": TransformParamFieldSpec(
                    schema=FloatParam(),
                ),
            },
            validator=validate_add_pedal_point_params,
        ),
    ),
    "stretto": ScoreTargetMotifsTransform(
        "stretto",
        stretto,
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    schema=StringParam(),
                    required=True,
                ),
                "num_times": TransformParamFieldSpec(
                    schema=IntegerParam(),
                    required=True,
                ),
                "spacing": TransformParamFieldSpec(
                    required=True,
                    schema=(EnumParam(allowed_values=tuple(NAMED_STRETTO_SPACINGS)), FloatParam()),
                ),
            }
        ),
    ),
    "frost_effect": ScoreTransform(
        "frost_effect",
        frost_effect,
        params_spec=TransformParamsSpec(
            fields={
                "iterations": TransformParamFieldSpec(
                    schema=IntegerParam(),
                )
            }
        ),
    ),
    "accelerando": PhraseTransform(
        "accelerando",
        accelerando_transform,
        params_spec=TransformParamsSpec(
            fields={
                "strength": TransformParamFieldSpec(
                    required=True,
                    schema=(EnumParam(allowed_values=tuple(INTENSITY_LEVELS)), FloatParam()),
                ),
                "jaggedness": TransformParamFieldSpec(
                    schema=(EnumParam(allowed_values=tuple(INTENSITY_LEVELS)), FloatParam()),
                ),
                "seed": TransformParamFieldSpec(
                    schema=IntegerParam(),
                ),
            }
        ),
    ),
    "ritardando": PhraseTransform(
        "ritardando",
        ritardando_transform,
        params_spec=TransformParamsSpec(
            fields={
                "strength": TransformParamFieldSpec(
                    required=True,
                    schema=(EnumParam(allowed_values=tuple(INTENSITY_LEVELS)), FloatParam()),
                ),
                "jaggedness": TransformParamFieldSpec(
                    schema=(EnumParam(allowed_values=tuple(INTENSITY_LEVELS)), FloatParam()),
                ),
                "seed": TransformParamFieldSpec(
                    schema=IntegerParam(),
                ),
            }
        ),
    ),
    "score_weierstrass": AllVoicesTransform(
        "score_weierstrass",
        apply_weierstrass_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "amplitude_scaling": TransformParamFieldSpec(schema=FloatParam()),
                "ripples_per_wave": TransformParamFieldSpec(schema=FloatParam()),
                "iterations": TransformParamFieldSpec(schema=IntegerParam()),
            }
        ),
    ),
    "weierstrass": PhraseTransform(
        "weierstrass",
        apply_weierstrass_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "amplitude_scaling": TransformParamFieldSpec(schema=FloatParam()),
                "ripples_per_wave": TransformParamFieldSpec(schema=FloatParam()),
                "iterations": TransformParamFieldSpec(schema=IntegerParam()),
            }
        ),
    ),
    "terraced_drift": PhraseTransform(
        "terraced_drift",
        apply_terraced_drift_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "step_size": TransformParamFieldSpec(schema=FloatParam()),
                "quantize_resolution": TransformParamFieldSpec(schema=FloatParam()),
            }
        ),
    ),
    "cellular_automata": PhraseTransform(
        "cellular_automata",
        apply_cellular_automata_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "rule": TransformParamFieldSpec(schema=IntegerParam()),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "width": TransformParamFieldSpec(schema=IntegerParam()),
            }
        ),
    ),
    "ridged_drop": PhraseTransform(
        "ridged_drop",
        apply_ridged_drop_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "octaves": TransformParamFieldSpec(schema=IntegerParam()),
                "ridge_density": TransformParamFieldSpec(schema=FloatParam()),
                "drop_when_noise_above": TransformParamFieldSpec(schema=FloatParam()),
            }
        ),
    ),
    "random_drop": PhraseTransform(
        "random_drop",
        apply_random_drop_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "drop_rate": TransformParamFieldSpec(schema=FloatParam()),
            }
        ),
    ),

    "score_terraced_drift": AllVoicesTransform(
        "score_terraced_drift",
        apply_terraced_drift_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "step_size": TransformParamFieldSpec(schema=FloatParam()),
                "quantize_resolution": TransformParamFieldSpec(schema=FloatParam()),
            }
        ),
    ),
    "score_cellular_automata": AllVoicesTransform(
        "score_cellular_automata",
        apply_cellular_automata_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "rule": TransformParamFieldSpec(schema=IntegerParam()),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "width": TransformParamFieldSpec(schema=IntegerParam()),
            }
        ),
    ),
    "score_ridged_drop": AllVoicesTransform(
        "score_ridged_drop",
        apply_ridged_drop_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "octaves": TransformParamFieldSpec(schema=IntegerParam()),
                "ridge_density": TransformParamFieldSpec(schema=FloatParam()),
                "drop_when_noise_above": TransformParamFieldSpec(schema=FloatParam()),
            }
        ),
    ),
    "score_random_drop": AllVoicesTransform(
        "score_random_drop",
        apply_random_drop_transform,
        params_spec=TransformParamsSpec(
            fields={
                "dimension": TransformParamFieldSpec(
                    required=True,
                    schema=EnumParam(allowed_values=tuple(ToneDimension)),
                ),
                "max_deviation": TransformParamFieldSpec(
                    schema=FloatParam(),
                    required=True,
                ),
                "seed": TransformParamFieldSpec(schema=IntegerParam()),
                "drop_rate": TransformParamFieldSpec(schema=FloatParam()),
            }
        ),
    ),
}
