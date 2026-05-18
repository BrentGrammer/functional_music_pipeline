from collections.abc import Callable, Mapping
from typing import cast

from score_model.motif import Motif
from score_model.phrase import Phrase
from transforms.base import (
    PhraseTransformDefinition,
    ScoreScope,
    ToneDimension,
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


PHRASE_TRANSFORMS: dict[str, PhraseTransformDefinition] = {
    "reverse": PhraseTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=reverse_tones([tone for motif in context.phrase.motifs for tone in motif.tones]),
                )
            ]
        ),
    ),
    "golden_ratio": PhraseTransformDefinition(
        name="golden_ratio",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=golden_ratio_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params.get("dimension", ToneDimension.DURATION)),
                    ),
                )
            ]
        ),
    ),
    "invert": PhraseTransformDefinition(
        name="invert",
        params_spec=INVERT_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=invert_tones([tone for motif in context.phrase.motifs for tone in motif.tones]),
                )
            ]
        ),
    ),
    "feigenbaum_sequence": PhraseTransformDefinition(
        name="feigenbaum_sequence",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=feigenbaum_sequence(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params.get("dimension", ToneDimension.DURATION)),
                    ),
                )
            ]
        ),
    ),
    "transpose": PhraseTransformDefinition(
        name="transpose",
        params_spec=TRANSPOSE_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=transpose_tones(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        semitones=cast(float, params["semitones"]),
                    ),
                )
            ]
        ),
    ),
    "scale": PhraseTransformDefinition(
        name="scale",
        params_spec=SCALE_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=scale_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params["dimension"]),
                        factor=cast(float, params["factor"]),
                    ),
                )
            ]
        ),
    ),
    "pad_silence": PhraseTransformDefinition(
        name="pad_silence",
        params_spec=PAD_SILENCE_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=pad_silence_tones(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        seconds=cast(float, params["seconds"]),
                        position=cast(str, params["position"]),
                    ),
                )
            ]
        ),
    ),
    "delay": PhraseTransformDefinition(
        name="delay",
        params_spec=DELAY_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=delay_tones(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        seconds=cast(float, params["seconds"]),
                    ),
                )
            ]
        ),
    ),
    "repeat": PhraseTransformDefinition(
        name="repeat",
        params_spec=REPEAT_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=repeat_tones(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        count=cast(int, params["count"]),
                    ),
                )
            ]
        ),
    ),
    "erosion": PhraseTransformDefinition(
        name="erosion",
        params_spec=EROSION_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=erosion_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params.get("dimension", ToneDimension.DURATION)),
                    ),
                )
            ]
        ),
    ),
    "drift": PhraseTransformDefinition(
        name="drift",
        params_spec=DRIFT_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=drift_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params["dimension"]),
                        rate=cast(float, params["rate"]),
                    ),
                )
            ]
        ),
    ),
    "phrase_feigenbaum_shrink": PhraseTransformDefinition(
        name="phrase_feigenbaum_shrink",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=phrase_feigenbaum_shrink(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        [
                            tone
                            for phrase in (
                                context.score.voices[context.voice_index].phrases[: context.phrase_index]
                                if context.phrase_index > 0
                                else context.score.voices[context.voice_index - 1].phrases
                                if context.voice_index > 0
                                else []
                            )
                            for motif in phrase.motifs
                            for tone in motif.tones
                        ],
                        dimension=cast(
                            ToneDimension | str,
                            params.get("dimension", ToneDimension.DURATION),
                        ),
                    ),
                )
            ]
        ),
    ),
    "phrase_feigenbaum_grow": PhraseTransformDefinition(
        name="phrase_feigenbaum_grow",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=phrase_feigenbaum_grow(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        [
                            tone
                            for phrase in (
                                context.score.voices[context.voice_index].phrases[: context.phrase_index]
                                if context.phrase_index > 0
                                else context.score.voices[context.voice_index - 1].phrases
                                if context.voice_index > 0
                                else []
                            )
                            for motif in phrase.motifs
                            for tone in motif.tones
                        ],
                        dimension=cast(
                            ToneDimension | str,
                            params.get("dimension", ToneDimension.DURATION),
                        ),
                    ),
                )
            ]
        ),
    ),
    "phrase_golden_ratio_shrink": PhraseTransformDefinition(
        name="phrase_golden_ratio_shrink",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=phrase_golden_ratio_shrink(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        [
                            tone
                            for phrase in (
                                context.score.voices[context.voice_index].phrases[: context.phrase_index]
                                if context.phrase_index > 0
                                else context.score.voices[context.voice_index - 1].phrases
                                if context.voice_index > 0
                                else []
                            )
                            for motif in phrase.motifs
                            for tone in motif.tones
                        ],
                        dimension=cast(
                            ToneDimension | str,
                            params.get("dimension", ToneDimension.DURATION),
                        ),
                    ),
                )
            ]
        ),
    ),
    "phrase_golden_ratio_grow": PhraseTransformDefinition(
        name="phrase_golden_ratio_grow",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=phrase_golden_ratio_grow(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        [
                            tone
                            for phrase in (
                                context.score.voices[context.voice_index].phrases[: context.phrase_index]
                                if context.phrase_index > 0
                                else context.score.voices[context.voice_index - 1].phrases
                                if context.voice_index > 0
                                else []
                            )
                            for motif in phrase.motifs
                            for tone in motif.tones
                        ],
                        dimension=cast(
                            ToneDimension | str,
                            params.get("dimension", ToneDimension.DURATION),
                        ),
                    ),
                )
            ]
        ),
    ),
    "accelerando": PhraseTransformDefinition(
        name="accelerando",
        params_spec=ACCELERANDO_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=accelerando_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        strength=cast(str | float, params.get("strength", "medium")),
                        jaggedness=cast(str | float, params.get("jaggedness", "none")),
                    ),
                )
            ]
        ),
    ),
    "ritardando": PhraseTransformDefinition(
        name="ritardando",
        params_spec=RITARDANDO_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=ritardando_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        strength=cast(str | float, params.get("strength", "medium")),
                        jaggedness=cast(str | float, params.get("jaggedness", "none")),
                    ),
                )
            ]
        ),
    ),
    "weierstrass": PhraseTransformDefinition(
        name="weierstrass",
        params_spec=WEIERSTRASS_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=apply_weierstrass_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params["dimension"]),
                        intensity=cast(str, params["intensity"]),
                    ),
                )
            ]
        ),
    ),
    "terraced_drift": PhraseTransformDefinition(
        name="terraced_drift",
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=apply_terraced_drift_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params["dimension"]),
                        max_step_change_pct=cast(int, params["max_step_change_pct"]),
                    ),
                )
            ]
        ),
    ),
    "cellular_automata": PhraseTransformDefinition(
        name="cellular_automata",
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=apply_cellular_automata_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params["dimension"]),
                        rule=cast(int, params["rule"]),
                        generations=cast(int, params["generations"]),
                        max_deviation=cast(float, params["max_deviation"]),
                    ),
                )
            ]
        ),
    ),
    "random_drop": PhraseTransformDefinition(
        name="random_drop",
        params_spec=RANDOM_DROP_PARAMS_SPEC,
        transform=lambda context, params: Phrase(
            motifs=[
                Motif(
                    name="<transformed>",
                    tones=apply_random_drop_transform(
                        [tone for motif in context.phrase.motifs for tone in motif.tones],
                        dimension=cast(ToneDimension | str, params["dimension"]),
                        max_drop_pct=cast(int, params["max_drop_pct"]),
                        drop_frequency_pct=cast(int, params["drop_frequency_pct"]),
                    ),
                )
            ]
        ),
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
