from transforms.base import (
    PhraseScope,
    ScoreScope,
    TransformDefinition,
)
from transforms.basic.delay import DELAY_PARAMS_SPEC, delay_tones
from transforms.basic.drift import DRIFT_PARAMS_SPEC, drift_transform
from transforms.basic.inversion import INVERT_PARAMS_SPEC, invert_tones
from transforms.basic.pad_silence import PAD_SILENCE_PARAMS_SPEC, pad_silence_tones
from transforms.basic.repeat import REPEAT_PARAMS_SPEC, repeat_tones
from transforms.basic.reversal import REVERSE_PARAMS_SPEC, reverse_tones
from transforms.basic.scale import SCALE_PARAMS_SPEC, scale_transform
from transforms.basic.transpose import TRANSPOSE_PARAMS_SPEC, transpose_tones
from transforms.complexity.cellular_automata import (
    CELLULAR_AUTOMATA_PARAMS_SPEC,
    apply_cellular_automata_transform,
)
from transforms.complexity.random_drop import RANDOM_DROP_PARAMS_SPEC, apply_random_drop_transform
from transforms.complexity.weierstrass import WEIERSTRASS_PARAMS_SPEC, apply_weierstrass_transform
from transforms.counterpoint.fugue import ADD_PEDAL_TONE_PARAMS_SPEC, STRETTO_PARAMS_SPEC, add_pedal_tone, stretto
from transforms.geological.erosion import EROSION_PARAMS_SPEC, erosion_transform
from transforms.geological.frost_effect import FROST_EFFECT_PARAMS_SPEC, frost_effect
from transforms.geological.terraced_drift import TERRACED_DRIFT_PARAMS_SPEC, apply_terraced_drift_transform
from transforms.proportion.feigenbaum import (
    FEIGENBAUM_PARAMS_SPEC,
    feigenbaum_sequence,
    phrase_feigenbaum_grow,
    phrase_feigenbaum_shrink,
    score_feigenbaum_sequence,
)
from transforms.proportion.golden_ratio import (
    GOLDEN_RATIO_PARAMS_SPEC,
    golden_ratio_transform,
    phrase_golden_ratio_grow,
    phrase_golden_ratio_shrink,
)
from transforms.tempo.accelerando import ACCELERANDO_PARAMS_SPEC, accelerando_transform
from transforms.tempo.ritardando import RITARDANDO_PARAMS_SPEC, ritardando_transform

PHRASE_TRANSFORMS: dict[str, TransformDefinition[PhraseScope]] = {
    "reverse": TransformDefinition(
        name="reverse",
        transform_func=reverse_tones,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=REVERSE_PARAMS_SPEC,
    ),
    "golden_ratio": TransformDefinition(
        name="golden_ratio",
        transform_func=golden_ratio_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
    ),
    "invert": TransformDefinition(
        name="invert",
        transform_func=invert_tones,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=INVERT_PARAMS_SPEC,
    ),
    "feigenbaum_sequence": TransformDefinition(
        name="feigenbaum_sequence",
        transform_func=feigenbaum_sequence,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=FEIGENBAUM_PARAMS_SPEC,
    ),
    "transpose": TransformDefinition(
        name="transpose",
        transform_func=transpose_tones,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=TRANSPOSE_PARAMS_SPEC,
    ),
    "scale": TransformDefinition(
        name="scale",
        transform_func=scale_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=SCALE_PARAMS_SPEC,
    ),
    "pad_silence": TransformDefinition(
        name="pad_silence",
        transform_func=pad_silence_tones,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=PAD_SILENCE_PARAMS_SPEC,
    ),
    "delay": TransformDefinition(
        name="delay",
        transform_func=delay_tones,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=DELAY_PARAMS_SPEC,
    ),
    "repeat": TransformDefinition(
        name="repeat",
        transform_func=repeat_tones,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=REPEAT_PARAMS_SPEC,
    ),
    "erosion": TransformDefinition(
        name="erosion",
        transform_func=erosion_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=EROSION_PARAMS_SPEC,
    ),
    "drift": TransformDefinition(
        name="drift",
        transform_func=drift_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=DRIFT_PARAMS_SPEC,
    ),
    "phrase_feigenbaum_shrink": TransformDefinition(
        name="phrase_feigenbaum_shrink",
        transform_func=phrase_feigenbaum_shrink,
        scope=PhraseScope.PHRASE_RELATIVE,
        params_spec=FEIGENBAUM_PARAMS_SPEC,
    ),
    "phrase_feigenbaum_grow": TransformDefinition(
        name="phrase_feigenbaum_grow",
        transform_func=phrase_feigenbaum_grow,
        scope=PhraseScope.PHRASE_RELATIVE,
        params_spec=FEIGENBAUM_PARAMS_SPEC,
    ),
    "phrase_golden_ratio_shrink": TransformDefinition(
        name="phrase_golden_ratio_shrink",
        transform_func=phrase_golden_ratio_shrink,
        scope=PhraseScope.PHRASE_RELATIVE,
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
    ),
    "phrase_golden_ratio_grow": TransformDefinition(
        name="phrase_golden_ratio_grow",
        transform_func=phrase_golden_ratio_grow,
        scope=PhraseScope.PHRASE_RELATIVE,
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
    ),
    "accelerando": TransformDefinition(
        name="accelerando",
        transform_func=accelerando_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=ACCELERANDO_PARAMS_SPEC,
    ),
    "ritardando": TransformDefinition(
        name="ritardando",
        transform_func=ritardando_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=RITARDANDO_PARAMS_SPEC,
    ),
    "weierstrass": TransformDefinition(
        name="weierstrass",
        transform_func=apply_weierstrass_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=WEIERSTRASS_PARAMS_SPEC,
    ),
    "terraced_drift": TransformDefinition(
        name="terraced_drift",
        transform_func=apply_terraced_drift_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
    ),
    "cellular_automata": TransformDefinition(
        name="cellular_automata",
        transform_func=apply_cellular_automata_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
    ),
    "random_drop": TransformDefinition(
        name="random_drop",
        transform_func=apply_random_drop_transform,
        scope=PhraseScope.OWN_PHRASE,
        params_spec=RANDOM_DROP_PARAMS_SPEC,
    ),
}

SCORE_TRANSFORMS: dict[str, TransformDefinition[ScoreScope]] = {
    "feigenbaum_sequence": TransformDefinition(
        name="feigenbaum_sequence",
        transform_func=score_feigenbaum_sequence,
        scope=ScoreScope.SCORE_AWARE,
        params_spec=FEIGENBAUM_PARAMS_SPEC,
    ),
    "reverse": TransformDefinition(
        name="reverse",
        transform_func=reverse_tones,
        scope=ScoreScope.EACH_VOICE,
        params_spec=REVERSE_PARAMS_SPEC,
    ),
    "golden_ratio": TransformDefinition(
        name="golden_ratio",
        transform_func=golden_ratio_transform,
        scope=ScoreScope.EACH_VOICE,
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
    ),
    "invert": TransformDefinition(
        name="invert",
        transform_func=invert_tones,
        scope=ScoreScope.EACH_VOICE,
        params_spec=INVERT_PARAMS_SPEC,
    ),
    "transpose": TransformDefinition(
        name="transpose",
        transform_func=transpose_tones,
        scope=ScoreScope.EACH_VOICE,
        params_spec=TRANSPOSE_PARAMS_SPEC,
    ),
    "scale": TransformDefinition(
        name="scale",
        transform_func=scale_transform,
        scope=ScoreScope.EACH_VOICE,
        params_spec=SCALE_PARAMS_SPEC,
    ),
    "delay": TransformDefinition(
        name="delay",
        transform_func=delay_tones,
        scope=ScoreScope.EACH_VOICE,
        params_spec=DELAY_PARAMS_SPEC,
    ),
    "repeat": TransformDefinition(
        name="repeat",
        transform_func=repeat_tones,
        scope=ScoreScope.EACH_VOICE,
        params_spec=REPEAT_PARAMS_SPEC,
    ),
    "drift": TransformDefinition(
        name="drift",
        transform_func=drift_transform,
        scope=ScoreScope.EACH_VOICE,
        params_spec=DRIFT_PARAMS_SPEC,
    ),
    "weierstrass": TransformDefinition(
        name="weierstrass",
        transform_func=apply_weierstrass_transform,
        scope=ScoreScope.EACH_VOICE,
        params_spec=WEIERSTRASS_PARAMS_SPEC,
    ),
    "terraced_drift": TransformDefinition(
        name="terraced_drift",
        transform_func=apply_terraced_drift_transform,
        scope=ScoreScope.EACH_VOICE,
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
    ),
    "cellular_automata": TransformDefinition(
        name="cellular_automata",
        transform_func=apply_cellular_automata_transform,
        scope=ScoreScope.EACH_VOICE,
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
    ),
    "random_drop": TransformDefinition(
        name="random_drop",
        transform_func=apply_random_drop_transform,
        scope=ScoreScope.EACH_VOICE,
        params_spec=RANDOM_DROP_PARAMS_SPEC,
    ),
    "add_pedal_tone": TransformDefinition(
        name="add_pedal_tone",
        transform_func=add_pedal_tone,
        scope=ScoreScope.SCORE_AWARE,
        params_spec=ADD_PEDAL_TONE_PARAMS_SPEC,
    ),
    "stretto": TransformDefinition(
        name="stretto",
        transform_func=stretto,
        scope=ScoreScope.TARGET_MOTIFS,
        params_spec=STRETTO_PARAMS_SPEC,
    ),
    "frost_effect": TransformDefinition(
        name="frost_effect",
        transform_func=frost_effect,
        scope=ScoreScope.SCORE_AWARE,
        params_spec=FROST_EFFECT_PARAMS_SPEC,
    ),
}
