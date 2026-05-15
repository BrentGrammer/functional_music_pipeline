from transforms.base import (
    EachVoiceTransform,
    EnumParam,
    FloatParam,
    IntegerParam,
    PhraseRelativeTransform,
    PhraseTransform,
    ScoreTargetMotifsTransform,
    ScoreTransform,
    ToneDimension,
    TransformParamFieldSpec,
    TransformParamsSpec,
    TransformWithCallable,
)
from transforms.delay import DELAY_PARAMS_SPEC, delay_tones
from transforms.drift import drift_transform
from transforms.duration import (
    ACCELERANDO_PARAMS_SPEC,
    RITARDANDO_PARAMS_SPEC,
    accelerando_transform,
    feigenbaum_sequence,
    phrase_feigenbaum_grow,
    phrase_feigenbaum_shrink,
    ritardando_transform,
    score_feigenbaum_sequence,
)
from transforms.erosion import erosion_transform
from transforms.frost import frost_effect
from transforms.fugue import ADD_PEDAL_POINT_PARAMS_SPEC, STRETTO_PARAMS_SPEC, add_pedal_point, stretto
from transforms.geological import (
    CELLULAR_AUTOMATA_PARAMS_SPEC,
    RANDOM_DROP_PARAMS_SPEC,
    RIDGED_DROP_PARAMS_SPEC,
    TERRACED_DRIFT_PARAMS_SPEC,
    WEIERSTRASS_PARAMS_SPEC,
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
from transforms.inversion import INVERT_PARAMS_SPEC, invert_tones
from transforms.pad_silence import PAD_SILENCE_PARAMS_SPEC, pad_silence_tones
from transforms.repeat import REPEAT_PARAMS_SPEC, repeat_tones
from transforms.reversal import REVERSE_PARAMS_SPEC, reverse_tones
from transforms.scale import scale_transform
from transforms.transpose import TRANSPOSE_PARAMS_SPEC, transpose_tones

TRANSFORMS: dict[str, TransformWithCallable] = {
    "reverse": PhraseTransform(
        "reverse",
        reverse_tones,
        params_spec=REVERSE_PARAMS_SPEC,
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
        params_spec=INVERT_PARAMS_SPEC,
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
        params_spec=TRANSPOSE_PARAMS_SPEC,
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
        params_spec=PAD_SILENCE_PARAMS_SPEC,
    ),
    "delay": PhraseTransform(
        "delay",
        delay_tones,
        params_spec=DELAY_PARAMS_SPEC,
    ),
    "repeat": PhraseTransform(
        "repeat",
        repeat_tones,
        params_spec=REPEAT_PARAMS_SPEC,
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
    "score_reverse": EachVoiceTransform(
        "score_reverse",
        reverse_tones,
        params_spec=REVERSE_PARAMS_SPEC,
    ),
    "score_golden_ratio": EachVoiceTransform(
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
    "score_invert": EachVoiceTransform(
        "score_invert",
        invert_tones,
        params_spec=INVERT_PARAMS_SPEC,
    ),
    "score_transpose": EachVoiceTransform(
        "score_transpose",
        transpose_tones,
        params_spec=TRANSPOSE_PARAMS_SPEC,
    ),
    "score_scale": EachVoiceTransform(
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
    "score_delay": EachVoiceTransform(
        "score_delay",
        delay_tones,
        params_spec=DELAY_PARAMS_SPEC,
    ),
    "score_repeat": EachVoiceTransform(
        "score_repeat",
        repeat_tones,
        params_spec=REPEAT_PARAMS_SPEC,
    ),
    "score_drift": EachVoiceTransform(
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
        params_spec=ADD_PEDAL_POINT_PARAMS_SPEC,
    ),
    "stretto": ScoreTargetMotifsTransform(
        "stretto",
        stretto,
        params_spec=STRETTO_PARAMS_SPEC,
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
        params_spec=ACCELERANDO_PARAMS_SPEC,
    ),
    "ritardando": PhraseTransform(
        "ritardando",
        ritardando_transform,
        params_spec=RITARDANDO_PARAMS_SPEC,
    ),
    "score_weierstrass": EachVoiceTransform(
        "score_weierstrass",
        apply_weierstrass_transform,
        params_spec=WEIERSTRASS_PARAMS_SPEC,
    ),
    "weierstrass": PhraseTransform(
        "weierstrass",
        apply_weierstrass_transform,
        params_spec=WEIERSTRASS_PARAMS_SPEC,
    ),
    "terraced_drift": PhraseTransform(
        "terraced_drift",
        apply_terraced_drift_transform,
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
    ),
    "cellular_automata": PhraseTransform(
        "cellular_automata",
        apply_cellular_automata_transform,
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
    ),
    "ridged_drop": PhraseTransform(
        "ridged_drop",
        apply_ridged_drop_transform,
        params_spec=RIDGED_DROP_PARAMS_SPEC,
    ),
    "random_drop": PhraseTransform(
        "random_drop",
        apply_random_drop_transform,
        params_spec=RANDOM_DROP_PARAMS_SPEC,
    ),

    "score_terraced_drift": EachVoiceTransform(
        "score_terraced_drift",
        apply_terraced_drift_transform,
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
    ),
    "score_cellular_automata": EachVoiceTransform(
        "score_cellular_automata",
        apply_cellular_automata_transform,
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
    ),
    "score_ridged_drop": EachVoiceTransform(
        "score_ridged_drop",
        apply_ridged_drop_transform,
        params_spec=RIDGED_DROP_PARAMS_SPEC,
    ),
    "score_random_drop": EachVoiceTransform(
        "score_random_drop",
        apply_random_drop_transform,
        params_spec=RANDOM_DROP_PARAMS_SPEC,
    ),
}
