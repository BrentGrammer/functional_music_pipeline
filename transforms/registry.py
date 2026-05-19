from typing import cast

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.traversal import flatten_voice_tones
from score_model.voice import Voice
from transforms.base import (
    PhraseTransformDefinition,
    ScoreTransformDefinition,
    ToneDimension,
)
from transforms.basic.delay import DELAY_PARAMS_SPEC, delay_phrase_transform, delay_tones
from transforms.basic.drift import DRIFT_PARAMS_SPEC, drift_phrase_transform, drift_transform
from transforms.basic.inversion import INVERT_PARAMS_SPEC, invert_phrase_transform, invert_tones
from transforms.basic.pad_silence import PAD_SILENCE_PARAMS_SPEC, pad_silence_phrase_transform, pad_silence_tones
from transforms.basic.repeat import REPEAT_PARAMS_SPEC, repeat_phrase_transform, repeat_tones
from transforms.basic.reversal import REVERSE_PARAMS_SPEC, reverse_phrase_transform, reverse_score_transform
from transforms.basic.scale import SCALE_PARAMS_SPEC, scale_phrase_transform, scale_transform
from transforms.basic.transpose import TRANSPOSE_PARAMS_SPEC, transpose_phrase_transform, transpose_tones
from transforms.complexity.cellular_automata import (
    CELLULAR_AUTOMATA_PARAMS_SPEC,
    apply_cellular_automata_transform,
    cellular_automata_phrase_transform,
)
from transforms.complexity.random_drop import RANDOM_DROP_PARAMS_SPEC, apply_random_drop_transform, random_drop_phrase_transform
from transforms.complexity.weierstrass import WEIERSTRASS_PARAMS_SPEC, apply_weierstrass_transform, weierstrass_phrase_transform
from transforms.counterpoint.fugue import (
    ADD_PEDAL_TONE_PARAMS_SPEC,
    STRETTO_PARAMS_SPEC,
    add_pedal_tone_score_transform,
    stretto_score_transform_adapter,
)
from transforms.geological.erosion import EROSION_PARAMS_SPEC, erosion_phrase_transform
from transforms.geological.frost_effect import FROST_EFFECT_PARAMS_SPEC, frost_effect
from transforms.geological.terraced_drift import TERRACED_DRIFT_PARAMS_SPEC, apply_terraced_drift_transform, terraced_drift_phrase_transform
from transforms.proportion.feigenbaum import (
    FEIGENBAUM_PARAMS_SPEC,
    feigenbaum_sequence,
    feigenbaum_sequence_phrase_transform,
    phrase_feigenbaum_grow_transform,
    phrase_feigenbaum_shrink_transform,
    score_feigenbaum_sequence,
)
from transforms.proportion.golden_ratio import (
    GOLDEN_RATIO_PARAMS_SPEC,
    golden_ratio_transform,
    golden_ratio_phrase_transform,
    phrase_golden_ratio_grow_transform,
    phrase_golden_ratio_shrink_transform,
)
from transforms.tempo.accelerando import ACCELERANDO_PARAMS_SPEC, accelerando_phrase_transform, accelerando_transform
from transforms.tempo.ritardando import RITARDANDO_PARAMS_SPEC, ritardando_phrase_transform, ritardando_transform

PHRASE_TRANSFORMS: dict[str, PhraseTransformDefinition] = {
    "reverse": PhraseTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform=reverse_phrase_transform,
    ),
    "golden_ratio": PhraseTransformDefinition(
        name="golden_ratio",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform=golden_ratio_phrase_transform,
    ),
    "invert": PhraseTransformDefinition(
        name="invert",
        params_spec=INVERT_PARAMS_SPEC,
        transform=invert_phrase_transform,
    ),
    "feigenbaum_sequence": PhraseTransformDefinition(
        name="feigenbaum_sequence",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform=feigenbaum_sequence_phrase_transform,
    ),
    "transpose": PhraseTransformDefinition(
        name="transpose",
        params_spec=TRANSPOSE_PARAMS_SPEC,
        transform=transpose_phrase_transform,
    ),
    "scale": PhraseTransformDefinition(
        name="scale",
        params_spec=SCALE_PARAMS_SPEC,
        transform=scale_phrase_transform,
    ),
    "pad_silence": PhraseTransformDefinition(
        name="pad_silence",
        params_spec=PAD_SILENCE_PARAMS_SPEC,
        transform=pad_silence_phrase_transform,
    ),
    "delay": PhraseTransformDefinition(
        name="delay",
        params_spec=DELAY_PARAMS_SPEC,
        transform=delay_phrase_transform,
    ),
    "repeat": PhraseTransformDefinition(
        name="repeat",
        params_spec=REPEAT_PARAMS_SPEC,
        transform=repeat_phrase_transform,
    ),
    "erosion": PhraseTransformDefinition(
        name="erosion",
        params_spec=EROSION_PARAMS_SPEC,
        transform=erosion_phrase_transform,
    ),
    "drift": PhraseTransformDefinition(
        name="drift",
        params_spec=DRIFT_PARAMS_SPEC,
        transform=drift_phrase_transform,
    ),
    "phrase_feigenbaum_shrink": PhraseTransformDefinition(
        name="phrase_feigenbaum_shrink",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform=phrase_feigenbaum_shrink_transform,
    ),
    "phrase_feigenbaum_grow": PhraseTransformDefinition(
        name="phrase_feigenbaum_grow",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform=phrase_feigenbaum_grow_transform,
    ),
    "phrase_golden_ratio_shrink": PhraseTransformDefinition(
        name="phrase_golden_ratio_shrink",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform=phrase_golden_ratio_shrink_transform,
    ),
    "phrase_golden_ratio_grow": PhraseTransformDefinition(
        name="phrase_golden_ratio_grow",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform=phrase_golden_ratio_grow_transform,
    ),
    "accelerando": PhraseTransformDefinition(
        name="accelerando",
        params_spec=ACCELERANDO_PARAMS_SPEC,
        transform=accelerando_phrase_transform,
    ),
    "ritardando": PhraseTransformDefinition(
        name="ritardando",
        params_spec=RITARDANDO_PARAMS_SPEC,
        transform=ritardando_phrase_transform,
    ),
    "weierstrass": PhraseTransformDefinition(
        name="weierstrass",
        params_spec=WEIERSTRASS_PARAMS_SPEC,
        transform=weierstrass_phrase_transform,
    ),
    "terraced_drift": PhraseTransformDefinition(
        name="terraced_drift",
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
        transform=terraced_drift_phrase_transform,
    ),
    "cellular_automata": PhraseTransformDefinition(
        name="cellular_automata",
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
        transform=cellular_automata_phrase_transform,
    ),
    "random_drop": PhraseTransformDefinition(
        name="random_drop",
        params_spec=RANDOM_DROP_PARAMS_SPEC,
        transform=random_drop_phrase_transform,
    ),
}

SCORE_TRANSFORMS: dict[str, ScoreTransformDefinition] = {
    "feigenbaum_sequence": ScoreTransformDefinition(
        name="feigenbaum_sequence",
        params_spec=FEIGENBAUM_PARAMS_SPEC,
        transform=lambda score, params: score_feigenbaum_sequence(score, **params),
    ),
    "reverse": ScoreTransformDefinition(
        name="reverse",
        params_spec=REVERSE_PARAMS_SPEC,
        transform=reverse_score_transform,
    ),
    "golden_ratio": ScoreTransformDefinition(
        name="golden_ratio",
        params_spec=GOLDEN_RATIO_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=golden_ratio_transform(
                                        flatten_voice_tones(voice),
                                        dimension=cast(
                                            ToneDimension | str,
                                            params.get("dimension", ToneDimension.DURATION),
                                        ),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "invert": ScoreTransformDefinition(
        name="invert",
        params_spec=INVERT_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=invert_tones(flatten_voice_tones(voice)),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "transpose": ScoreTransformDefinition(
        name="transpose",
        params_spec=TRANSPOSE_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=transpose_tones(
                                        flatten_voice_tones(voice),
                                        semitones=cast(float, params["semitones"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "scale": ScoreTransformDefinition(
        name="scale",
        params_spec=SCALE_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=scale_transform(
                                        flatten_voice_tones(voice),
                                        dimension=cast(ToneDimension | str, params["dimension"]),
                                        factor=cast(float, params["factor"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "delay": ScoreTransformDefinition(
        name="delay",
        params_spec=DELAY_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=delay_tones(
                                        flatten_voice_tones(voice),
                                        seconds=cast(float, params["seconds"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "repeat": ScoreTransformDefinition(
        name="repeat",
        params_spec=REPEAT_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=repeat_tones(
                                        flatten_voice_tones(voice),
                                        count=cast(int, params["count"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "drift": ScoreTransformDefinition(
        name="drift",
        params_spec=DRIFT_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=drift_transform(
                                        flatten_voice_tones(voice),
                                        dimension=cast(ToneDimension | str, params["dimension"]),
                                        rate=cast(float, params["rate"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "weierstrass": ScoreTransformDefinition(
        name="weierstrass",
        params_spec=WEIERSTRASS_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=apply_weierstrass_transform(
                                        flatten_voice_tones(voice),
                                        dimension=cast(ToneDimension | str, params["dimension"]),
                                        intensity=cast(str, params["intensity"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "terraced_drift": ScoreTransformDefinition(
        name="terraced_drift",
        params_spec=TERRACED_DRIFT_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=apply_terraced_drift_transform(
                                        flatten_voice_tones(voice),
                                        dimension=cast(ToneDimension | str, params["dimension"]),
                                        max_step_change_pct=cast(int, params["max_step_change_pct"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "cellular_automata": ScoreTransformDefinition(
        name="cellular_automata",
        params_spec=CELLULAR_AUTOMATA_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=apply_cellular_automata_transform(
                                        flatten_voice_tones(voice),
                                        dimension=cast(ToneDimension | str, params["dimension"]),
                                        rule=cast(int, params["rule"]),
                                        generations=cast(int, params["generations"]),
                                        max_deviation=cast(float, params["max_deviation"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "random_drop": ScoreTransformDefinition(
        name="random_drop",
        params_spec=RANDOM_DROP_PARAMS_SPEC,
        transform=lambda score, params: Score(
            voices=[
                Voice(
                    phrases=[
                        Phrase(
                            motifs=[
                                Motif(
                                    name="<each_voice>",
                                    tones=apply_random_drop_transform(
                                        flatten_voice_tones(voice),
                                        dimension=cast(ToneDimension | str, params["dimension"]),
                                        max_drop_pct=cast(int, params["max_drop_pct"]),
                                        drop_frequency_pct=cast(int, params["drop_frequency_pct"]),
                                    ),
                                )
                            ]
                        )
                    ]
                )
                for voice in score.voices
            ]
        ),
    ),
    "add_pedal_tone": ScoreTransformDefinition(
        name="add_pedal_tone",
        params_spec=ADD_PEDAL_TONE_PARAMS_SPEC,
        transform=lambda score, params: add_pedal_tone_score_transform(score, params),
    ),
    "stretto": ScoreTransformDefinition(
        name="stretto",
        params_spec=STRETTO_PARAMS_SPEC,
        transform=lambda score, params: stretto_score_transform_adapter(score, params),
    ),
    "frost_effect": ScoreTransformDefinition(
        name="frost_effect",
        params_spec=FROST_EFFECT_PARAMS_SPEC,
        transform=lambda score, params: frost_effect(score, **params),
    ),
}
