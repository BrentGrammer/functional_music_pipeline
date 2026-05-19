import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext, ToneDimension
from transforms.basic.delay import delay_phrase_transform, delay_score_transform
from transforms.basic.inversion import invert_phrase_transform, invert_score_transform
from transforms.basic.repeat import repeat_phrase_transform, repeat_score_transform
from transforms.basic.transpose import transpose_phrase_transform, transpose_score_transform
from transforms.complexity.cellular_automata import cellular_automata_phrase_transform, cellular_automata_score_transform
from transforms.complexity.random_drop import random_drop_phrase_transform, random_drop_score_transform
from transforms.complexity.weierstrass import weierstrass_phrase_transform, weierstrass_score_transform
from transforms.geological.terraced_drift import terraced_drift_phrase_transform, terraced_drift_score_transform
from transforms.proportion.feigenbaum import feigenbaum_sequence_phrase_transform
from transforms.proportion.golden_ratio import golden_ratio_score_transform
from transforms.tempo.accelerando import accelerando_phrase_transform
from transforms.tempo.ritardando import ritardando_phrase_transform


def _make_test_score(*, voices: list[Voice] | None = None) -> Score:
    if voices is not None:
        return Score(voices=voices)
    return Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="a", tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)])]),
                    Phrase(motifs=[Motif(name="b", tones=[Tone(440.0, duration=1.0)])]),
                ]
            ),
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="c", tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)])])
                ]
            ),
        ]
    )


def test_repeat_phrase_transform_rejects_bool_count():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="repeat-target", tones=[Tone(220.0, duration=0.5)])])
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        repeat_phrase_transform(context, {"count": True})


def test_transpose_score_transform_rejects_bool_semitones():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="transpose-target", tones=[Tone(220.0, duration=0.5)])])
                ]
            )
        ]
    )

    with pytest.raises(ValueError):
        transpose_score_transform(score, {"semitones": True})


def test_transpose_phrase_transform_rejects_bool_semitones():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="transpose-target", tones=[Tone(220.0, duration=0.5)])])
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        transpose_phrase_transform(context, {"semitones": True})


def test_delay_score_transform_rejects_bool_seconds():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="delay-target", tones=[Tone(220.0, duration=0.5)])])
                ]
            )
        ]
    )

    with pytest.raises(ValueError):
        delay_score_transform(score, {"seconds": True})


def test_delay_phrase_transform_rejects_bool_seconds():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="delay-target", tones=[Tone(220.0, duration=0.5)])])
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        delay_phrase_transform(context, {"seconds": True})


def test_repeat_score_transform_rejects_bool_count():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="repeat-target", tones=[Tone(220.0, duration=0.5)])])
                ]
            )
        ]
    )

    with pytest.raises(ValueError):
        repeat_score_transform(score, {"count": True})


def test_invert_phrase_transform_rejects_bool_dimension():
    score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="x", tones=[Tone(0.0), Tone(10.0)])])])])
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        invert_phrase_transform(context, {"dimension": True})


def test_invert_score_transform_rejects_bool_dimension():
    score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="x", tones=[Tone(0.0), Tone(10.0)])])])])

    with pytest.raises(ValueError):
        invert_score_transform(score, {"dimension": True})


def test_cellular_automata_transforms_reject_invalid_param_types():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="automata-target",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    params = {"dimension": ToneDimension.DURATION, "rule": 30, "generations": 2, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        cellular_automata_phrase_transform(context, {**params, "rule": 30.0})

    with pytest.raises(ValueError):
        cellular_automata_score_transform(score, {**params, "generations": True})


def test_cellular_automata_transforms_reject_invalid_dimension_type():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="automata-target",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    params = {"rule": 30, "generations": 2, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        cellular_automata_phrase_transform(context, {**params, "dimension": 1})

    with pytest.raises(ValueError):
        cellular_automata_score_transform(score, {**params, "dimension": []})


def test_cellular_automata_phrase_transform_rejects_non_integer_generations():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="automata-target",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    params = {"dimension": ToneDimension.DURATION, "rule": 30, "generations": 2.0, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        cellular_automata_phrase_transform(context, params)


def test_cellular_automata_score_transform_rejects_non_integer_rule():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="automata-target",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    params = {"dimension": ToneDimension.DURATION, "rule": 30.0, "generations": 2, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        cellular_automata_score_transform(score, params)


def test_cellular_automata_transforms_reject_invalid_max_deviation_type():
    score = Score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="automata-target",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    params = {"dimension": ToneDimension.DURATION, "rule": 30, "generations": 2}

    with pytest.raises(ValueError):
        cellular_automata_phrase_transform(context, {**params, "max_deviation": True})

    with pytest.raises(ValueError):
        cellular_automata_score_transform(score, {**params, "max_deviation": "0.3"})


def test_random_drop_transforms_reject_invalid_param_types():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="drop-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "amplitude", "max_drop_pct": 20, "drop_frequency_pct": 80}

    with pytest.raises(ValueError):
        random_drop_phrase_transform(context, {**params, "max_drop_pct": "20"})

    with pytest.raises(ValueError):
        random_drop_score_transform(score, {**params, "drop_frequency_pct": True})


def test_random_drop_transforms_reject_invalid_dimension_type():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="drop-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"max_drop_pct": 20, "drop_frequency_pct": 80}

    with pytest.raises(ValueError):
        random_drop_phrase_transform(context, {**params, "dimension": 123})

    with pytest.raises(ValueError):
        random_drop_score_transform(score, {**params, "dimension": []})


def test_random_drop_score_transform_rejects_non_integer_max_drop_pct():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="drop-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    params = {"dimension": "amplitude", "max_drop_pct": 20.0, "drop_frequency_pct": 80}

    with pytest.raises(ValueError):
        random_drop_score_transform(score, params)


def test_random_drop_phrase_transform_rejects_non_integer_drop_frequency_pct():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="drop-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        random_drop_phrase_transform(
            context,
            {"dimension": "amplitude", "max_drop_pct": 20, "drop_frequency_pct": 80.0},
        )


def test_terraced_drift_transforms_reject_invalid_param_types():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="drift-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        terraced_drift_phrase_transform(context, {"dimension": None, "max_step_change_pct": 25})

    with pytest.raises(ValueError):
        terraced_drift_phrase_transform(context, {"dimension": "frequency", "max_step_change_pct": True})

    with pytest.raises(ValueError):
        terraced_drift_score_transform(score, {"dimension": "frequency", "max_step_change_pct": True})

    with pytest.raises(ValueError):
        terraced_drift_score_transform(score, {"dimension": 1, "max_step_change_pct": 25})


def test_golden_ratio_score_transform_rejects_non_dimension_value():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="first-phrase",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    ),
                    Phrase(
                        motifs=[
                            Motif(
                                name="second-phrase",
                                tones=[Tone(440.0, duration=1.0)],
                            )
                        ]
                    ),
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="cross-voice-phrase",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )

    with pytest.raises(ValueError):
        golden_ratio_score_transform(score, {"dimension": 3})


def test_weierstrass_transforms_reject_invalid_param_types():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="weierstrass-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        weierstrass_phrase_transform(context, {"dimension": None, "intensity": "medium"})

    with pytest.raises(ValueError):
        weierstrass_phrase_transform(context, {"dimension": "frequency", "intensity": 1})

    with pytest.raises(ValueError):
        weierstrass_score_transform(score, {"dimension": 1, "intensity": "medium"})

    with pytest.raises(ValueError):
        weierstrass_score_transform(score, {"dimension": "frequency", "intensity": True})


def test_feigenbaum_phrase_transform_rejects_non_dimension_value():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(motifs=[Motif(name="other-voice", tones=[Tone(220.0, duration=0.5)])])
                ]
            ),
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="feigenbaum-target",
                                tones=[Tone(550.0, duration=0.25), Tone(660.0, duration=0.25)],
                            )
                        ]
                    )
                ]
            ),
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)

    with pytest.raises(ValueError):
        feigenbaum_sequence_phrase_transform(context, {"dimension": 1})


def test_accelerando_phrase_transform_rejects_invalid_param_types():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="accelerando-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        accelerando_phrase_transform(context, {"strength": True, "jaggedness": "none"})

    with pytest.raises(ValueError):
        accelerando_phrase_transform(context, {"strength": "medium", "jaggedness": []})


def test_ritardando_phrase_transform_rejects_invalid_param_types():
    score = _make_test_score(
        voices=[
            Voice(
                phrases=[
                    Phrase(
                        motifs=[
                            Motif(
                                name="ritardando-target",
                                tones=[Tone(220.0, duration=0.5), Tone(330.0, duration=0.5)],
                            )
                        ]
                    )
                ]
            )
        ]
    )
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        ritardando_phrase_transform(context, {"strength": {}, "jaggedness": "none"})

    with pytest.raises(ValueError):
        ritardando_phrase_transform(context, {"strength": "medium", "jaggedness": True})
