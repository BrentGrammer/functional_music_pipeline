import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import PhraseTransformContext
from transforms.basic.delay import delay_score_transform
from transforms.basic.inversion import invert_phrase_transform
from transforms.basic.repeat import repeat_phrase_transform
from transforms.basic.transpose import transpose_score_transform
from transforms.complexity.cellular_automata import cellular_automata_phrase_transform, cellular_automata_score_transform
from transforms.complexity.random_drop import random_drop_phrase_transform, random_drop_score_transform
from transforms.geological.terraced_drift import terraced_drift_phrase_transform, terraced_drift_score_transform
from transforms.proportion.feigenbaum import feigenbaum_sequence_phrase_transform
from transforms.proportion.golden_ratio import golden_ratio_score_transform


def _build_score() -> Score:
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
    score = _build_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        repeat_phrase_transform(context, {"count": True})


def test_transpose_score_transform_rejects_bool_semitones():
    score = _build_score()

    with pytest.raises(ValueError):
        transpose_score_transform(score, {"semitones": True})


def test_delay_score_transform_rejects_bool_seconds():
    score = _build_score()

    with pytest.raises(ValueError):
        delay_score_transform(score, {"seconds": True})


def test_invert_phrase_transform_rejects_bool_dimension():
    score = Score(voices=[Voice(phrases=[Phrase(motifs=[Motif(name="x", tones=[Tone(0.0), Tone(10.0)])])])])
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        invert_phrase_transform(context, {"dimension": True})


def test_cellular_automata_transforms_reject_invalid_param_types():
    score = _build_score()
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)
    params = {"dimension": "duration", "rule": 30, "generations": 2, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        cellular_automata_phrase_transform(context, {**params, "rule": 30.0})

    with pytest.raises(ValueError):
        cellular_automata_score_transform(score, {**params, "generations": True})


def test_random_drop_transforms_reject_invalid_param_types():
    score = _build_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)
    params = {"dimension": "amplitude", "max_drop_pct": 20, "drop_frequency_pct": 80}

    with pytest.raises(ValueError):
        random_drop_phrase_transform(context, {**params, "max_drop_pct": "20"})

    with pytest.raises(ValueError):
        random_drop_score_transform(score, {**params, "drop_frequency_pct": True})


def test_terraced_drift_transforms_reject_invalid_param_types():
    score = _build_score()
    context = PhraseTransformContext(score=score, voice_index=0, phrase_index=0)

    with pytest.raises(ValueError):
        terraced_drift_phrase_transform(context, {"dimension": None, "max_step_change_pct": 25})

    with pytest.raises(ValueError):
        terraced_drift_score_transform(score, {"dimension": "frequency", "max_step_change_pct": True})


def test_golden_ratio_score_transform_rejects_non_dimension_value():
    score = _build_score()

    with pytest.raises(ValueError):
        golden_ratio_score_transform(score, {"dimension": 3})


def test_feigenbaum_phrase_transform_rejects_non_dimension_value():
    score = _build_score()
    context = PhraseTransformContext(score=score, voice_index=1, phrase_index=0)

    with pytest.raises(ValueError):
        feigenbaum_sequence_phrase_transform(context, {"dimension": 1})
