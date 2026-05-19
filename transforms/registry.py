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
from transforms.basic.delay import DELAY_PARAMS_SPEC, delay_tones
from transforms.basic.drift import DRIFT_PARAMS_SPEC, drift_transform
from transforms.basic.inversion import INVERT_PARAMS_SPEC, invert_tones
from transforms.basic.pad_silence import PAD_SILENCE_PARAMS_SPEC, pad_silence_tones
from transforms.basic.repeat import REPEAT_PARAMS_SPEC, repeat_tones
from transforms.basic.reversal import REVERSE_PARAMS_SPEC, reverse_phrase_transform, reverse_score_transform, reverse_tones
from transforms.basic.scale import SCALE_PARAMS_SPEC, scale_transform
from transforms.basic.transpose import TRANSPOSE_PARAMS_SPEC, transpose_tones
from transforms.complexity.cellular_automata import (
    CELLULAR_AUTOMATA_PARAMS_SPEC,
    apply_cellular_automata_transform,
)
from transforms.complexity.random_drop import RANDOM_DROP_PARAMS_SPEC, apply_random_drop_transform
from transforms.complexity.weierstrass import WEIERSTRASS_PARAMS_SPEC, apply_weierstrass_transform
from transforms.counterpoint.fugue import (
    ADD_PEDAL_TONE_PARAMS_SPEC,
    STRETTO_PARAMS_SPEC,
    add_pedal_tone_score_transform,
    stretto_score_transform_adapter,
)
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
        transform=reverse_phrase_transform,
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
