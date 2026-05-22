import pytest

from score_model.motif import Motif
from score_model.phrase import Phrase
from score_model.score import Score
from score_model.tone import Tone
from score_model.voice import Voice
from transforms.base import ToneDimension
from transforms.basic.delay import DELAY_PARAMS_SPEC
from transforms.basic.inversion import INVERT_PARAMS_SPEC
from transforms.basic.repeat import REPEAT_PARAMS_SPEC
from transforms.basic.transpose import TRANSPOSE_PARAMS_SPEC
from transforms.complexity.cellular_automata import CELLULAR_AUTOMATA_PARAMS_SPEC
from transforms.complexity.random_drop import RANDOM_DROP_PARAMS_SPEC
from transforms.complexity.weierstrass import WEIERSTRASS_PARAMS_SPEC
from transforms.geological.terraced_drift import TERRACED_DRIFT_PARAMS_SPEC


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
    with pytest.raises(ValueError):
        REPEAT_PARAMS_SPEC.parse_params({"count": True}, transform_name="repeat")


def test_transpose_score_transform_rejects_bool_semitones():
    with pytest.raises(ValueError):
        TRANSPOSE_PARAMS_SPEC.parse_params({"semitones": True}, transform_name="transpose")


def test_transpose_phrase_transform_rejects_bool_semitones():
    with pytest.raises(ValueError):
        TRANSPOSE_PARAMS_SPEC.parse_params({"semitones": True}, transform_name="transpose")


def test_delay_score_transform_rejects_bool_seconds():
    with pytest.raises(ValueError):
        DELAY_PARAMS_SPEC.parse_params({"seconds": True}, transform_name="delay")


def test_delay_phrase_transform_rejects_bool_seconds():
    with pytest.raises(ValueError):
        DELAY_PARAMS_SPEC.parse_params({"seconds": True}, transform_name="delay")


def test_repeat_score_transform_rejects_bool_count():
    with pytest.raises(ValueError):
        REPEAT_PARAMS_SPEC.parse_params({"count": True}, transform_name="repeat")


def test_invert_phrase_transform_rejects_bool_dimension():
    with pytest.raises(ValueError):
        INVERT_PARAMS_SPEC.parse_params({"dimension": True}, transform_name="invert")


def test_invert_score_transform_rejects_bool_dimension():
    with pytest.raises(ValueError):
        INVERT_PARAMS_SPEC.parse_params({"dimension": True}, transform_name="invert")


def test_cellular_automata_transforms_reject_invalid_param_types():
    params = {"dimension": ToneDimension.DURATION, "rule": 30, "generations": 2, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params({**params, "rule": 30.0}, transform_name="cellular_automata")

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params({**params, "generations": True}, transform_name="cellular_automata")


def test_cellular_automata_transforms_reject_invalid_dimension_type():
    params = {"rule": 30, "generations": 2, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params({**params, "dimension": 1}, transform_name="cellular_automata")

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params({**params, "dimension": []}, transform_name="cellular_automata")


def test_cellular_automata_phrase_transform_rejects_non_integer_generations():
    params = {"dimension": ToneDimension.DURATION, "rule": 30, "generations": 2.0, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params(params, transform_name="cellular_automata")


def test_cellular_automata_score_transform_rejects_non_integer_rule():
    params = {"dimension": ToneDimension.DURATION, "rule": 30.0, "generations": 2, "max_deviation": 0.3}

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params(params, transform_name="cellular_automata")


def test_cellular_automata_transforms_reject_invalid_max_deviation_type():
    params = {"dimension": ToneDimension.DURATION, "rule": 30, "generations": 2}

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params({**params, "max_deviation": True}, transform_name="cellular_automata")

    with pytest.raises(ValueError):
        CELLULAR_AUTOMATA_PARAMS_SPEC.parse_params({**params, "max_deviation": "0.3"}, transform_name="cellular_automata")


def test_random_drop_transforms_reject_invalid_param_types():
    params = {"dimension": ToneDimension.AMPLITUDE, "max_drop_pct": 20, "drop_frequency_pct": 80}

    with pytest.raises(ValueError):
        RANDOM_DROP_PARAMS_SPEC.parse_params({**params, "max_drop_pct": "20"}, transform_name="random_drop")

    with pytest.raises(ValueError):
        RANDOM_DROP_PARAMS_SPEC.parse_params({**params, "drop_frequency_pct": True}, transform_name="random_drop")


def test_random_drop_transforms_reject_invalid_dimension_type():
    params = {"max_drop_pct": 20, "drop_frequency_pct": 80}

    with pytest.raises(ValueError):
        RANDOM_DROP_PARAMS_SPEC.parse_params({**params, "dimension": 123}, transform_name="random_drop")

    with pytest.raises(ValueError):
        RANDOM_DROP_PARAMS_SPEC.parse_params({**params, "dimension": []}, transform_name="random_drop")


def test_random_drop_score_transform_rejects_non_integer_max_drop_pct():
    params = {"dimension": ToneDimension.AMPLITUDE, "max_drop_pct": 20.0, "drop_frequency_pct": 80}

    with pytest.raises(ValueError):
        RANDOM_DROP_PARAMS_SPEC.parse_params(params, transform_name="random_drop")


def test_random_drop_phrase_transform_rejects_non_integer_drop_frequency_pct():
    with pytest.raises(ValueError):
        RANDOM_DROP_PARAMS_SPEC.parse_params(
            {"dimension": ToneDimension.AMPLITUDE, "max_drop_pct": 20, "drop_frequency_pct": 80.0},
            transform_name="random_drop",
        )


def test_terraced_drift_transforms_reject_invalid_param_types():
    with pytest.raises(ValueError):
        TERRACED_DRIFT_PARAMS_SPEC.parse_params({"dimension": None, "max_step_change_pct": 25}, transform_name="terraced_drift")

    with pytest.raises(ValueError):
        TERRACED_DRIFT_PARAMS_SPEC.parse_params(
            {"dimension": ToneDimension.FREQUENCY, "max_step_change_pct": True},
            transform_name="terraced_drift",
        )

    with pytest.raises(ValueError):
        TERRACED_DRIFT_PARAMS_SPEC.parse_params(
            {"dimension": ToneDimension.FREQUENCY, "max_step_change_pct": True},
            transform_name="terraced_drift",
        )

    with pytest.raises(ValueError):
        TERRACED_DRIFT_PARAMS_SPEC.parse_params({"dimension": 1, "max_step_change_pct": 25}, transform_name="terraced_drift")


def test_golden_ratio_score_transform_rejects_non_dimension_value():
    from transforms.proportion.golden_ratio import GOLDEN_RATIO_PARAMS_SPEC
    with pytest.raises(ValueError):
        GOLDEN_RATIO_PARAMS_SPEC.parse_params({"dimension": 3}, transform_name="golden_ratio")


def test_weierstrass_transforms_reject_invalid_param_types():
    with pytest.raises(ValueError):
        WEIERSTRASS_PARAMS_SPEC.parse_params({"dimension": None, "intensity": "medium"}, transform_name="weierstrass")

    with pytest.raises(ValueError):
        WEIERSTRASS_PARAMS_SPEC.parse_params({"dimension": ToneDimension.FREQUENCY, "intensity": 1}, transform_name="weierstrass")

    with pytest.raises(ValueError):
        WEIERSTRASS_PARAMS_SPEC.parse_params({"dimension": 1, "intensity": "medium"}, transform_name="weierstrass")

    with pytest.raises(ValueError):
        WEIERSTRASS_PARAMS_SPEC.parse_params({"dimension": ToneDimension.FREQUENCY, "intensity": True}, transform_name="weierstrass")


def test_feigenbaum_phrase_transform_rejects_non_dimension_value():
    from transforms.proportion.feigenbaum import FEIGENBAUM_PARAMS_SPEC
    with pytest.raises(ValueError):
        FEIGENBAUM_PARAMS_SPEC.parse_params({"dimension": 1}, transform_name="feigenbaum_sequence")


def test_accelerando_phrase_transform_rejects_invalid_param_types():
    from transforms.tempo.accelerando import ACCELERANDO_PARAMS_SPEC
    with pytest.raises(ValueError):
        ACCELERANDO_PARAMS_SPEC.parse_params({"strength": True, "jaggedness": "none"}, transform_name="accelerando")

    with pytest.raises(ValueError):
        ACCELERANDO_PARAMS_SPEC.parse_params({"strength": "medium", "jaggedness": []}, transform_name="accelerando")


def test_ritardando_phrase_transform_rejects_invalid_param_types():
    from transforms.tempo.ritardando import RITARDANDO_PARAMS_SPEC
    with pytest.raises(ValueError):
        RITARDANDO_PARAMS_SPEC.parse_params({"strength": {}, "jaggedness": "none"}, transform_name="ritardando")

    with pytest.raises(ValueError):
        RITARDANDO_PARAMS_SPEC.parse_params({"strength": "medium", "jaggedness": True}, transform_name="ritardando")
