
from transforms.base import (
    PhraseTransformDefinition,
    RegisteredPhraseTransform,
    RegisteredScoreTransform,
    ScoreTransformDefinition,
)
from transforms.basic.delay import DELAY_PARAMS_SPEC, delay_phrase_transform, delay_score_transform
from transforms.basic.drift import DRIFT_PARAMS_SPEC, drift_phrase_transform, drift_score_transform
from transforms.basic.inversion import INVERT_PARAMS_SPEC, invert_phrase_transform, invert_score_transform
from transforms.basic.pad_silence import PAD_SILENCE_PARAMS_SPEC, pad_silence_phrase_transform, pad_silence_score_transform
from transforms.basic.repeat import REPEAT_PARAMS_SPEC, repeat_phrase_transform, repeat_score_transform
from transforms.basic.reversal import REVERSE_PARAMS_SPEC, reverse_phrase_transform, reverse_score_transform
from transforms.basic.scale import SCALE_PARAMS_SPEC, scale_phrase_transform, scale_score_transform
from transforms.basic.transpose import TRANSPOSE_PARAMS_SPEC, transpose_phrase_transform, transpose_score_transform
from transforms.complexity.cellular_automata import (
    CELLULAR_AUTOMATA_PARAMS_SPEC,
    cellular_automata_phrase_transform,
    cellular_automata_score_transform,
)
from transforms.complexity.random_drop import RANDOM_DROP_PARAMS_SPEC, random_drop_phrase_transform, random_drop_score_transform
from transforms.complexity.weierstrass import WEIERSTRASS_PARAMS_SPEC, weierstrass_phrase_transform, weierstrass_score_transform
from transforms.counterpoint.fugue import (
    ADD_PEDAL_TONE_PARAMS_SPEC,
    STRETTO_PARAMS_SPEC,
    add_pedal_tone_score_transform,
    stretto_score_transform_adapter,
)
from transforms.geological.erosion import EROSION_PARAMS_SPEC, erosion_phrase_transform
from transforms.geological.fragment import FRAGMENT_PARAMS_SPEC, fragment_phrase_transform
from transforms.geological.frost_effect import FROST_EFFECT_PARAMS_SPEC, frost_effect_score_transform_adapter
from transforms.geological.terraced_drift import TERRACED_DRIFT_PARAMS_SPEC, terraced_drift_phrase_transform, terraced_drift_score_transform
from transforms.proportion.feigenbaum import (
    FEIGENBAUM_PARAMS_SPEC,
    feigenbaum_sequence_phrase_transform,
    feigenbaum_sequence_score_transform,
    phrase_feigenbaum_grow_transform,
    phrase_feigenbaum_shrink_transform,
)
from transforms.proportion.golden_ratio import (
    GOLDEN_RATIO_PARAMS_SPEC,
    golden_ratio_single_phrase_transform,
    phrase_relative_golden_ratio_grow_transform,
    phrase_relative_golden_ratio_shrink_transform,
    score_golden_ratio_grow_transform,
    score_golden_ratio_shrink_transform,
)
from transforms.tempo.accelerando import ACCELERANDO_PARAMS_SPEC, accelerando_phrase_transform
from transforms.tempo.ritardando import RITARDANDO_PARAMS_SPEC, ritardando_phrase_transform

PHRASE_TRANSFORMS: dict[str, RegisteredPhraseTransform] = {
    "reverse": PhraseTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform_function=reverse_phrase_transform,
    ),
    "golden_ratio": PhraseTransformDefinition(
        name="golden_ratio",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform_function=golden_ratio_single_phrase_transform,
    ),
    "invert": PhraseTransformDefinition(
        name="invert",
        params_spec=INVERT_PARAMS_SPEC,
        transform_function=invert_phrase_transform,
    ),
    "feigenbaum_sequence": PhraseTransformDefinition(
        name="feigenbaum_sequence",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform_function=feigenbaum_sequence_phrase_transform,
    ),
    "transpose": PhraseTransformDefinition(
        name="transpose",
        params_spec=TRANSPOSE_PARAMS_SPEC,
        transform_function=transpose_phrase_transform,
    ),
    "scale": PhraseTransformDefinition(
        name="scale",
        params_spec=SCALE_PARAMS_SPEC,
        transform_function=scale_phrase_transform,
    ),
    "pad_silence": PhraseTransformDefinition(
        name="pad_silence",
        params_spec=PAD_SILENCE_PARAMS_SPEC,
        transform_function=pad_silence_phrase_transform,
    ),
    "delay": PhraseTransformDefinition(
        name="delay",
        params_spec=DELAY_PARAMS_SPEC,
        transform_function=delay_phrase_transform,
    ),
    "repeat": PhraseTransformDefinition(
        name="repeat",
        params_spec=REPEAT_PARAMS_SPEC,
        transform_function=repeat_phrase_transform,
    ),
    "erosion": PhraseTransformDefinition(
        name="erosion",
        params_spec=EROSION_PARAMS_SPEC,
        transform_function=erosion_phrase_transform,
    ),
    "fragment": PhraseTransformDefinition(
        name="fragment",
        params_spec=FRAGMENT_PARAMS_SPEC,
        transform_function=fragment_phrase_transform,
    ),
    "drift": PhraseTransformDefinition(
        name="drift",
        params_spec=DRIFT_PARAMS_SPEC,
        transform_function=drift_phrase_transform,
    ),
    "phrase_feigenbaum_shrink": PhraseTransformDefinition(
        name="phrase_feigenbaum_shrink",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform_function=phrase_feigenbaum_shrink_transform,
    ),
    "phrase_feigenbaum_grow": PhraseTransformDefinition(
        name="phrase_feigenbaum_grow",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform_function=phrase_feigenbaum_grow_transform,
    ),
    "phrase_relative_golden_ratio_shrink": PhraseTransformDefinition(
        name="phrase_relative_golden_ratio_shrink",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform_function=phrase_relative_golden_ratio_shrink_transform,
    ),
    "phrase_relative_golden_ratio_grow": PhraseTransformDefinition(
        name="phrase_relative_golden_ratio_grow",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform_function=phrase_relative_golden_ratio_grow_transform,
    ),
    "accelerando": PhraseTransformDefinition(
        name="accelerando",
        params_spec=ACCELERANDO_PARAMS_SPEC,
        transform_function=accelerando_phrase_transform,
    ),
    "ritardando": PhraseTransformDefinition(
        name="ritardando",
        params_spec=RITARDANDO_PARAMS_SPEC,
        transform_function=ritardando_phrase_transform,
    ),
    "weierstrass": PhraseTransformDefinition(
        name="weierstrass",
        params_spec=WEIERSTRASS_PARAMS_SPEC,
        transform_function=weierstrass_phrase_transform,
    ),
    "terraced_drift": PhraseTransformDefinition(
        name="terraced_drift",
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
        transform_function=terraced_drift_phrase_transform,
    ),
    "cellular_automata": PhraseTransformDefinition(
        name="cellular_automata",
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
        transform_function=cellular_automata_phrase_transform,
    ),
    "random_drop": PhraseTransformDefinition(
        name="random_drop",
        params_spec=RANDOM_DROP_PARAMS_SPEC,
        transform_function=random_drop_phrase_transform,
    ),
}

SCORE_TRANSFORMS: dict[str, RegisteredScoreTransform] = {
    "feigenbaum_sequence": ScoreTransformDefinition(
        name="feigenbaum_sequence",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform_function=feigenbaum_sequence_score_transform,
    ),
    "reverse": ScoreTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform_function=reverse_score_transform,
    ),
    "score_golden_ratio_shrink": ScoreTransformDefinition(
        name="score_golden_ratio_shrink",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform_function=score_golden_ratio_shrink_transform,
    ),
    "score_golden_ratio_grow": ScoreTransformDefinition(
        name="score_golden_ratio_grow",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform_function=score_golden_ratio_grow_transform,
    ),
    "invert": ScoreTransformDefinition(
        name="invert",
        params_spec=INVERT_PARAMS_SPEC,
        transform_function=invert_score_transform,
    ),
    "transpose": ScoreTransformDefinition(
        name="transpose",
        params_spec=TRANSPOSE_PARAMS_SPEC,
        transform_function=transpose_score_transform,
    ),
    "scale": ScoreTransformDefinition(
        name="scale",
        params_spec=SCALE_PARAMS_SPEC,
        transform_function=scale_score_transform,
    ),
    "pad_silence": ScoreTransformDefinition(
        name="pad_silence",
        params_spec=PAD_SILENCE_PARAMS_SPEC,
        transform_function=pad_silence_score_transform,
    ),
    "delay": ScoreTransformDefinition(
        name="delay",
        params_spec=DELAY_PARAMS_SPEC,
        transform_function=delay_score_transform,
    ),
    "repeat": ScoreTransformDefinition(
        name="repeat",
        params_spec=REPEAT_PARAMS_SPEC,
        transform_function=repeat_score_transform,
    ),
    "drift": ScoreTransformDefinition(
        name="drift",
        params_spec=DRIFT_PARAMS_SPEC,
        transform_function=drift_score_transform,
    ),
    "weierstrass": ScoreTransformDefinition(
        name="weierstrass",
        params_spec=WEIERSTRASS_PARAMS_SPEC,
        transform_function=weierstrass_score_transform,
    ),
    "terraced_drift": ScoreTransformDefinition(
        name="terraced_drift",
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
        transform_function=terraced_drift_score_transform,
    ),
    "cellular_automata": ScoreTransformDefinition(
        name="cellular_automata",
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
        transform_function=cellular_automata_score_transform,
    ),
    "random_drop": ScoreTransformDefinition(
        name="random_drop",
        params_spec=RANDOM_DROP_PARAMS_SPEC,
        transform_function=random_drop_score_transform,
    ),
    "add_pedal_tone": ScoreTransformDefinition(
        name="add_pedal_tone",
        params_spec=ADD_PEDAL_TONE_PARAMS_SPEC,
        transform_function=add_pedal_tone_score_transform,
    ),
    "stretto": ScoreTransformDefinition(
        name="stretto",
        params_spec=STRETTO_PARAMS_SPEC,
        transform_function=stretto_score_transform_adapter,
    ),
    "frost_effect": ScoreTransformDefinition(
        name="frost_effect",
        params_spec=FROST_EFFECT_PARAMS_SPEC,
        transform_function=frost_effect_score_transform_adapter,
    ),
}
