import pytest

from composition.parser import (
    _apply_all_voices_transform_with_optional_params,
    _apply_phrase_transform_spec,
    _apply_score_transform,
    _apply_transform_with_optional_params,
    TRANSFORMS,
    parse_composition,
    parse_motifs,
    parse_phrase,
    parse_transform_spec,
    resolve_profile_in_params,
)
from composition.schema import GeologicalTransformParams, TransformConfig
from score_model.tone import Tone
from score_model.score import Score
from score_model.math_constants import FEIGENBAUM_DELTA, GOLDEN_RATIO
from transforms.base import (
    ToneDimension,
    TransformDescriptor,
    TransformParamFieldSpec,
    TransformParamType,
    TransformParamsSpec,
    TransformScope,
)
from transforms.profiles import WeierstrassProfile


def test_stretto_spacing_descriptor_accepts_named_or_float_spacing():
    spacing_spec = TRANSFORMS["stretto"].params_spec.fields["spacing"]

    assert spacing_spec.param_type == (TransformParamType.ENUM, TransformParamType.FLOAT)
    assert spacing_spec.required is True
    assert spacing_spec.allowed_enum_values == ("golden_ratio", "feigenbaum_delta")


@pytest.mark.parametrize("transform_name", ["accelerando", "ritardando"])
def test_tempo_curve_descriptor_accepts_preset_or_float_controls(transform_name):
    fields = TRANSFORMS[transform_name].params_spec.fields

    assert fields["strength"].param_type == (TransformParamType.ENUM, TransformParamType.FLOAT)
    assert fields["strength"].required is True
    assert fields["strength"].allowed_enum_values == ("none", "low", "medium", "high", "extreme")
    assert fields["jaggedness"].param_type == (TransformParamType.ENUM, TransformParamType.FLOAT)
    assert fields["jaggedness"].required is False
    assert fields["jaggedness"].allowed_enum_values == ("none", "low", "medium", "high", "extreme")


def test_fixed_string_descriptors_use_enum_metadata():
    position_spec = TRANSFORMS["pad_silence"].params_spec.fields["position"]
    mode_spec = TRANSFORMS["add_pedal_point"].params_spec.fields["mode"]

    assert position_spec.param_type is TransformParamType.ENUM
    assert position_spec.allowed_enum_values == ("start", "end")
    assert mode_spec.param_type is TransformParamType.ENUM
    assert mode_spec.allowed_enum_values == ("sustain", "repeat")


def test_parse_motifs():
    motifs_dict = {
        "seed_a": ["440:0.25", "880"],
        "seed_b": ["523.25"]
    }

    result = parse_motifs(motifs_dict)

    assert "seed_a" in result
    assert len(result["seed_a"]) == 2
    assert result["seed_a"][0].frequency == 440.0
    assert result["seed_a"][0].duration == 0.25
    assert result["seed_a"][1].frequency == 880.0

    assert "seed_b" in result
    assert len(result["seed_b"]) == 1
    assert result["seed_b"][0].frequency == 523.25

def test_parse_motifs_requires_object_mapping():
    with pytest.raises(ValueError):
        parse_motifs(["440"])

def test_parse_motifs_requires_list_values():
    with pytest.raises(ValueError):
        parse_motifs({"seed_a": "440"})

def test_parse_phrase_single_motif_from_motifs_list():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5), Tone(880, 0.5)]
    }

    phrase_dict = {
        "motifs": ["seed_a"],
        "transforms": ["reverse"]
    }

    result = parse_phrase(phrase_dict, parsed_motifs)

    assert len(result) == 2
    assert result[0].frequency == 880.0
    assert result[1].frequency == 440.0

def test_parse_phrase_multiple_motifs():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)],
        "seed_b": [Tone(880, 0.25), Tone(523.25, 0.75)]
    }

    phrase_dict = {
        "motifs": ["seed_a", "seed_b"]
    }

    result = parse_phrase(phrase_dict, parsed_motifs)

    assert len(result) == 3
    assert result[0].frequency == 440.0
    assert result[0].duration == 0.5
    assert result[1].frequency == 880.0
    assert result[1].duration == 0.25
    assert result[2].frequency == 523.25
    assert result[2].duration == 0.75

def test_parse_phrase_reverse_applies_after_grouping_motifs():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5), Tone(660, 0.25)],
        "seed_b": [Tone(880, 0.75)]
    }

    phrase_dict = {
        "motifs": ["seed_a", "seed_b"],
        "transforms": ["reverse"]
    }

    result = parse_phrase(phrase_dict, parsed_motifs)

    assert len(result) == 3
    assert [tone.frequency for tone in result] == [880.0, 660.0, 440.0]
    assert [tone.duration for tone in result] == [0.75, 0.25, 0.5]

def test_parse_phrase_scale_applies_to_all_grouped_motifs():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)],
        "seed_b": [Tone(880, 0.25), Tone(523.25, 0.75)]
    }

    phrase_dict = {
        "motifs": ["seed_a", "seed_b"],
        "transforms": [{"name": "scale", "params": {"dimension": "duration", "factor": 2.0}}]
    }

    result = parse_phrase(phrase_dict, parsed_motifs)

    assert len(result) == 3
    assert result[0].duration == 1.0
    assert result[1].duration == 0.5
    assert result[2].duration == 1.5

def test_parse_phrase_delay_applies_to_all_grouped_motifs():
    EXPECTED_TONE_COUNT_WITH_DELAY = 2
    SILENCE_FREQUENCY = 0.0
    SILENCE_AMPLITUDE = 0.0
    ORIGINAL_FREQUENCY = 440.0
    ORIGINAL_DURATION = 0.5
    DELAY_SECONDS = 1.8

    parsed_motifs = {"seed_a": [Tone(ORIGINAL_FREQUENCY, ORIGINAL_DURATION)]}
    phrase_dict = {
        "motifs": ["seed_a"],
        "transforms": [{"name": "delay", "params": {"seconds": DELAY_SECONDS}}],
    }

    result = parse_phrase(phrase_dict, parsed_motifs)

    assert len(result) == EXPECTED_TONE_COUNT_WITH_DELAY
    assert result[0].frequency == pytest.approx(SILENCE_FREQUENCY)
    assert result[0].amplitude == pytest.approx(SILENCE_AMPLITUDE)
    assert result[0].duration == pytest.approx(DELAY_SECONDS)
    assert result[1].frequency == pytest.approx(ORIGINAL_FREQUENCY)
    assert result[1].duration == pytest.approx(ORIGINAL_DURATION)

class TestScaleTransformParsing:
    def test_scale_duration(self):
        original_duration = 0.5
        parsed_motifs = {"seed_a": [Tone(440, original_duration)]}

        factor = 0.5
        phrase_dict = {
            "motifs": ["seed_a"],
            "transforms": [{"name": "scale", "params": {"dimension": "duration", "factor": factor}}],
        }

        result = parse_phrase(phrase_dict, parsed_motifs)

        assert len(result) == 1
        assert result[0].duration == original_duration * factor

    def test_scale_frequency(self):
        original_frequency = 440.0
        factor = 1.5
        parsed_motifs = {"seed": [Tone(original_frequency, 0.5)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [
                {
                    "name": "scale",
                    "params": {"dimension": "frequency", "factor": factor},
                }
            ],
        }
        result = parse_phrase(phrase_config, parsed_motifs)
        assert len(result) == 1
        assert result[0].frequency == pytest.approx(original_frequency * factor)
        assert result[0].duration == 0.5

    def test_scale_amplitude(self):
        original_amplitude = 0.5
        factor = 0.8
        parsed_motifs = {"seed": [Tone(440, 0.5, amplitude=original_amplitude)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [
                {
                    "name": "scale",
                    "params": {"dimension": "amplitude", "factor": factor},
                }
            ],
        }
        result = parse_phrase(phrase_config, parsed_motifs)
        assert len(result) == 1
        assert result[0].amplitude == pytest.approx(original_amplitude * factor)
        assert result[0].frequency == 440.0

    def test_scale_with_numeric_param_raises_error(self):
        # Ensures the 'scale' transform enforces explicit parameterization,
        # preventing ambiguous default behavior.
        parsed_motifs = {"seed": [Tone(440)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [{"name": "scale", "params": 2.0}],
        }
        with pytest.raises(ValueError):
            parse_phrase(phrase_config, parsed_motifs)

    def test_scale_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["scale"]
        valid_params = {"dimension": "duration", "factor": 2.0}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "scale", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_score_scale_with_numeric_param_raises_error(self):
        # Ensures the score-level 'scale' transform enforces explicit parameterization.
        composition_doc = {
            "motifs": {"seed": ["440"]},
            "composition": {
                "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                "score_transforms": [{"name": "score_scale", "params": 2.0}],
            },
        }
        with pytest.raises(ValueError):
            parse_composition(composition_doc)

    def test_score_scale_with_missing_required_fields_raises_error(self):
        descriptor = TRANSFORMS["score_scale"]
        valid_params = {"dimension": "duration", "factor": 2.0}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "score_scale", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                parse_composition(composition_doc)

    def test_transpose_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["transpose"]
        valid_params = {"semitones": 1.0}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "transpose", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_score_transpose_with_missing_required_fields_raises_error(self):
        descriptor = TRANSFORMS["score_transpose"]
        valid_params = {"semitones": 1.0}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "score_transpose", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                parse_composition(composition_doc)

    def test_reverse_rejects_unknown_top_level_params(self):
        parsed_motifs = {"seed": [Tone(440)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [{"name": "reverse", "params": {"unexpected": True}}],
        }

        with pytest.raises(ValueError):
            parse_phrase(phrase_config, parsed_motifs)

    @pytest.mark.parametrize(
        ("transform_name", "valid_params"),
        [
            ("transpose", {"semitones": 1.0}),
            ("delay", {"seconds": 0.25}),
            ("repeat", {"count": 2}),
        ],
    )
    def test_required_param_transforms_reject_unknown_top_level_params(
        self,
        transform_name: str,
        valid_params: dict[str, float | int],
    ):
        parsed_motifs = {"seed": [Tone(440)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [
                {
                    "name": transform_name,
                    "params": {
                        **valid_params,
                        "unexpected": 123,
                    },
                }
            ],
        }

        with pytest.raises(ValueError):
            parse_phrase(phrase_config, parsed_motifs)

    def test_delay_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["delay"]
        valid_params = {"seconds": 0.25}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "delay", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_score_delay_with_missing_required_fields_raises_error(self):
        descriptor = TRANSFORMS["score_delay"]
        valid_params = {"seconds": 0.25}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "score_delay", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                parse_composition(composition_doc)

    def test_repeat_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["repeat"]
        valid_params = {"count": 2}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "repeat", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_score_repeat_with_missing_required_fields_raises_error(self):
        descriptor = TRANSFORMS["score_repeat"]
        valid_params = {"count": 2}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "score_repeat", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                parse_composition(composition_doc)

    def test_accelerando_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["accelerando"]
        valid_params = {"strength": "medium", "jaggedness": "none"}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "accelerando", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_ritardando_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["ritardando"]
        valid_params = {"strength": "medium", "jaggedness": "none"}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "ritardando", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_drift_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["drift"]
        valid_params = {"dimension": "frequency", "rate": 0.1}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "drift", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_score_drift_with_missing_required_fields_raises_error(self):
        descriptor = TRANSFORMS["score_drift"]
        valid_params = {"dimension": "frequency", "rate": 0.1}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "score_drift", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                parse_composition(composition_doc)

    def test_geological_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = TRANSFORMS["geological"]
        valid_params = {
            "profile": {"type": "weierstrass", "params": {"seed": 42}},
            "dimension": "frequency",
            "max_deviation": 0.1,
        }

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "geological", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                parse_phrase(phrase_config, parsed_motifs)

    def test_score_geological_with_missing_required_fields_raises_error(self):
        descriptor = TRANSFORMS["score_geological"]
        valid_params = {
            "profile": {"type": "weierstrass", "params": {"seed": 42}},
            "dimension": "frequency",
            "max_deviation": 0.1,
        }

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "score_geological", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                parse_composition(composition_doc)

    def test_add_pedal_point_with_missing_required_fields_raises_error(self):
        descriptor = TRANSFORMS["add_pedal_point"]
        valid_params = {"frequency": 130.81, "duration": 2.0, "amplitude": 0.25}

        for required_field in descriptor.params_spec.required_fields:
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {},
                "composition": {
                    "voices": [],
                    "score_transforms": [{"name": "add_pedal_point", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                parse_composition(composition_doc)

def test_parse_phrase_with_reference_transform():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)]
    }
    reference_tones = [Tone(110, 1.0)]

    phrase_dict = {
        "motifs": ["seed_a"],
        "transforms": ["phrase_golden_ratio_grow"]
    }

    result = parse_phrase(phrase_dict, parsed_motifs, reference_tones)

    assert len(result) == 1
    assert result[0].duration == pytest.approx(1.0 * GOLDEN_RATIO)

def test_parse_phrase_reference_transform_uses_total_grouped_phrase_duration():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)],
        "seed_b": [Tone(880, 0.5)]
    }
    reference_tones = [Tone(110, 2.0)]

    phrase_dict = {
        "motifs": ["seed_a", "seed_b"],
        "transforms": ["phrase_golden_ratio_grow"]
    }

    result = parse_phrase(phrase_dict, parsed_motifs, reference_tones)

    assert len(result) == 2
    expected_total_duration = 2.0 * GOLDEN_RATIO
    actual_total_duration = sum(tone.duration for tone in result)
    assert actual_total_duration == pytest.approx(expected_total_duration)
    assert result[0].duration == pytest.approx(expected_total_duration / 2.0)
    assert result[1].duration == pytest.approx(expected_total_duration / 2.0)

def test_parse_composition_multi_motif_phrase_followed_by_phrase_uses_phrase_level_reference():
    json_data = {
        "motifs": {
            "seed_a": ["440:0.5"],
            "seed_b": ["660:0.5"],
            "seed_c": ["880:1.0"]
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {"motifs": ["seed_a", "seed_b"]},
                        {"motifs": ["seed_c"], "transforms": ["phrase_feigenbaum_shrink"]}
                    ]
                }
            ]
        }
    }

    score = parse_composition(json_data)

    assert len(score.voices) == 1
    assert len(score.voices[0]) == 3

    assert score.voices[0][0].frequency == 440.0
    assert score.voices[0][0].duration == 0.5
    assert score.voices[0][1].frequency == 660.0
    assert score.voices[0][1].duration == 0.5

    expected_third_duration = 1.0 / FEIGENBAUM_DELTA
    assert score.voices[0][2].frequency == 880.0
    assert score.voices[0][2].duration == pytest.approx(expected_third_duration)

def test_parse_phrase_missing_motifs():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"transforms": ["reverse"]}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_phrase_empty_motifs():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": []}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_phrase_non_list_motifs():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": "seed_a"}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_phrase_motifs_entries_must_be_non_empty_strings():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a", ""]}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_phrase_unknown_motif():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["missing"]}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_phrase_requires_phrase_object():
    parsed_motifs = {"seed_a": [Tone(440)]}

    with pytest.raises(ValueError):
        parse_phrase(["seed_a"], parsed_motifs)

def test_parse_phrase_transforms_must_be_a_list():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a"], "transforms": "reverse"}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_phrase_transform_object_requires_name():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a"], "transforms": [{"params": 2.0}]}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_phrase_transform_must_be_string_or_object():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a"], "transforms": [123]}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)

def test_parse_transform_spec_rejects_scalar_params():
    transform_spec = {"name": "transpose", "params": 1.0}

    with pytest.raises(ValueError):
        parse_transform_spec(transform_spec, "Phrase")


def test_parse_phrase_unknown_transform():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a"], "transforms": ["unknown_transform"]}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)


def test_parse_phrase_requires_params_object_when_transform_params_are_missing():
    parsed_motifs = {"seed": [Tone(440)]}
    phrase_dict = {"motifs": ["seed"], "transforms": [{"name": "scale"}]}

    with pytest.raises(ValueError):
        parse_phrase(phrase_dict, parsed_motifs)


def test_apply_transform_with_optional_params_rejects_non_dict_non_none_params():
    with pytest.raises(AssertionError):
        _apply_transform_with_optional_params(lambda tones: tones, [], 1.0)


def test_apply_score_transform_rejects_non_dict_non_none_params():
    descriptor = TransformDescriptor(
        "_test_score_transform",
        TransformScope.SCORE,
        lambda score: score,
    )

    with pytest.raises(AssertionError):
        _apply_score_transform(Score([]), descriptor, 1.0)


def test_apply_all_voices_transform_with_optional_params_rejects_non_dict_non_none_params():
    with pytest.raises(AssertionError):
        _apply_all_voices_transform_with_optional_params(lambda tones: tones, Score([]), 1.0)


def test_apply_phrase_transform_spec_rejects_non_dict_non_none_params_for_relative_scope():
    descriptor = TransformDescriptor(
        "_test_phrase_relative_transform",
        TransformScope.PHRASE_RELATIVE,
        lambda phrase_tones, reference_tones: phrase_tones,
    )

    with pytest.raises(AssertionError):
        _apply_phrase_transform_spec(descriptor, [Tone(440)], 1.0, [Tone(220)])

def test_parse_composition_requires_document_object():
    with pytest.raises(ValueError):
        parse_composition([])

def test_parse_composition_requires_motifs_object():
    with pytest.raises(ValueError):
        parse_composition({"motifs": [], "composition": {}})

def test_parse_composition_requires_composition_object():
    with pytest.raises(ValueError):
        parse_composition({"motifs": {}, "composition": []})

def test_parse_composition_requires_voices_list():
    with pytest.raises(ValueError):
        parse_composition({"motifs": {}, "composition": {"voices": {}}})

def test_parse_composition_requires_voice_objects():
    with pytest.raises(ValueError):
        parse_composition({"motifs": {}, "composition": {"voices": ["voice_a"]}})

def test_parse_composition_requires_phrases_list():
    with pytest.raises(ValueError):
        parse_composition({"motifs": {}, "composition": {"voices": [{"phrases": {}}]}})

def test_parse_composition_score_transforms_must_be_list():
    with pytest.raises(ValueError):
        parse_composition({"motifs": {}, "composition": {"voices": [], "score_transforms": {}}})

def test_parse_composition_score_transform_object_requires_name():
    json_data = {
        "motifs": {},
        "composition": {
            "voices": [],
            "score_transforms": [{"params": 2.0}]
        }
    }

    with pytest.raises(ValueError):
        parse_composition(json_data)

def test_parse_composition_unknown_score_transform():
    json_data = {
        "motifs": {},
        "composition": {
            "voices": [],
            "score_transforms": ["score_unknown"]
        }
    }

    with pytest.raises(ValueError):
        parse_composition(json_data)


def test_parse_composition_rejects_phrase_transform_in_score_transforms():
    json_data = {
        "motifs": {"seed": ["440:0.5", "660:0.5"]},
        "composition": {
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
            "score_transforms": ["reverse"],
        },
    }

    with pytest.raises(ValueError):
        parse_composition(json_data)


def test_parse_composition_score_reverse_applies_to_all_voices_without_params():
    json_data = {
        "motifs": {
            "voice_a": ["440:0.5", "660:0.25"],
            "voice_b": ["880:0.75", "990:1.0"],
        },
        "composition": {
            "voices": [
                {"phrases": [{"motifs": ["voice_a"]}]},
                {"phrases": [{"motifs": ["voice_b"]}]},
            ],
            "score_transforms": ["score_reverse"],
        },
    }

    score = parse_composition(json_data)

    assert [tone.frequency for tone in score.voices[0].tones] == [660.0, 440.0]
    assert [tone.duration for tone in score.voices[0].tones] == [0.25, 0.5]
    assert [tone.frequency for tone in score.voices[1].tones] == [990.0, 880.0]
    assert [tone.duration for tone in score.voices[1].tones] == [1.0, 0.75]

def test_parse_composition():
    json_data = {
        "motifs": {
            "seed_a": ["440:0.5"],
            "seed_b": ["880:0.5"]
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {"motifs": ["seed_a"], "transforms": ["reverse"]}
                    ]
                },
                {
                    "phrases": [
                        {"motifs": ["seed_b"], "transforms": []}
                    ]
                }
            ],
            "score_transforms": ["score_feigenbaum_sequence"]
        }
    }

    score = parse_composition(json_data)

    assert isinstance(score, Score)
    assert len(score.voices) == 2
    assert len(score.voices[0]) == 1
    assert len(score.voices[1]) == 1

    assert score.voices[0][0].frequency == 440.0
    assert score.voices[0][0].duration == 0.5

    assert score.voices[1][0].frequency == 880.0
    assert score.voices[1][0].duration == pytest.approx(0.5 / FEIGENBAUM_DELTA)

def test_parse_composition_with_value_score_transform():
    factor = 2.0
    original_duration = 0.5
    json_data = {
        "motifs": {
            "seed": [f"440:{original_duration}"]
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {"motifs": ["seed"]}
                    ]
                }
            ],
            "score_transforms": [
                {"name": "score_scale", "params": {"dimension": "duration", "factor": factor}}
            ]
        }
    }

    score = parse_composition(json_data)

    assert len(score.voices) == 1
    assert score.voices[0][0].duration == original_duration * factor

def test_schema_allows_geological_transform_params():
    # Verifies that schema types accommodate the unified geological transform.
    # This is a static type check; it passes if mypy/pyright don't complain.
    params: GeologicalTransformParams = {
        "profile": {"type": "weierstrass", "params": {"seed": 42}},
        "dimension": "FREQUENCY",
        "max_deviation": 0.1,
    }
    transform: TransformConfig = {
        "name": "geological",
        "params": params,
    }

    # This test primarily serves to validate the type hinting schema.
    # A simple runtime assertion confirms the object was created.
    assert transform["name"] == "geological"
    assert isinstance(transform["params"], dict)


def test_parse_transform_spec_allows_pre_resolved_profile_instance():
    # Verifies that a params dict containing a non-primitive object (a profile
    # instance) can pass through validation, which is necessary after pre-processing.
    profile_instance = WeierstrassProfile(seed=42)
    transform_spec = {
        "name": "geological",
        "params": {
            "profile": profile_instance,
            "dimension": "FREQUENCY",
            "max_deviation": 0.1,
        },
    }

    # parse_transform_spec does not validate the inner contents of the params dict,
    # so this should pass without raising an error.
    name, params = parse_transform_spec(transform_spec, "Phrase")

    assert name == "geological"
    assert isinstance(params, dict)
    assert params["profile"] is profile_instance


class TestResolveProfileInParams:
    def test_pass_through_if_no_profile_key(self):
        params = {"dimension": "FREQUENCY", "max_deviation": 0.1}
        result = resolve_profile_in_params(params)
        assert result is params  # Should be the same object

    def test_pass_through_if_params_not_dict(self):
        assert resolve_profile_in_params(5) == 5
        assert resolve_profile_in_params(None) is None

    def test_resolves_profile_dict_to_instance(self):
        params: GeologicalTransformParams = {
            "profile": {"type": "weierstrass", "params": {"seed": 123}},
            "dimension": "FREQUENCY",
            "max_deviation": 0.1,
        }
        result = resolve_profile_in_params(params)
        assert isinstance(result, dict)
        assert isinstance(result["profile"], WeierstrassProfile)
        assert result["profile"].seed == 123
        assert result["dimension"] == "FREQUENCY"

    def test_propagates_error_from_build_profile(self):
        params = {"profile": {"type": "nonexistent"}}
        with pytest.raises(ValueError):
            resolve_profile_in_params(params)


def test_parse_phrase_with_geological_transform_prebuilt_profile():
    # Verifies the 'geological' transform is correctly registered and callable,
    # bypassing the JSON factory to test dispatch logic in isolation.
    parsed_motifs = {"seed": [Tone(440.0)]}
    phrase_config = {
        "motifs": ["seed"],
        "transforms": [
            {
                "name": "geological",
                "params": {
                    "profile": WeierstrassProfile(seed=42),
                    "dimension": ToneDimension.FREQUENCY,
                    "max_deviation": 0.1,
                },
            }
        ],
    }

    # The `resolve_profile_in_params` helper will eventually be idempotent, so passing an
    # already-resolved profile instance will work correctly. For now, this tests dispatch.
    result = parse_phrase(phrase_config, parsed_motifs)
    assert len(result) == 1
    assert result[0].frequency != 440.0
    assert 440.0 * 0.9 <= result[0].frequency <= 440.0 * 1.1


@pytest.mark.parametrize(
    "profile_config",
    [
        {"type": "weierstrass", "params": {"seed": 42}},
        {"type": "terraced", "params": {"seed": 42}},
        {"type": "cellular_automata", "params": {"seed": 42, "rule": 30}},
        # The default drop_when_noise_above threshold for ridged_multifractal is
        # high enough that a short sequence may produce all zeros. We lower it here
        # to guarantee a transformation occurs for this test.
        {"type": "ridged_multifractal", "params": {"seed": 42, "drop_when_noise_above": 0.1}},
    ],
    ids=["weierstrass", "terraced", "cellular_automata", "ridged_multifractal"],
)
def test_parse_phrase_with_unified_geological_transform_from_json(profile_config):
    # End-to-end test verifying the parser correctly handles the full JSON ->
    # profile factory -> transform application pipeline for all profile types.
    json_data = {
        "motifs": {"seed": ["440:1.0" for _ in range(5)]},
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["seed"],
                            "transforms": [
                                {
                                    "name": "geological",
                                    "params": {
                                        "profile": profile_config,
                                        "dimension": "FREQUENCY",
                                        "max_deviation": 0.1,
                                    },
                                }
                            ],
                        }
                    ]
                }
            ]
        },
    }

    score = parse_composition(json_data)
    assert len(score.voices) == 1
    voice_tones = score.voices[0].tones
    assert len(voice_tones) == 5
    # Check that frequencies were transformed, not left at 440.0
    assert any(t.frequency != 440.0 for t in voice_tones)


def test_parse_composition_with_score_geological_transform():
    # Verifies the score-level 'score_geological' transform is wired correctly.
    json_data = {
        "motifs": {"seed": ["440:0.5", "880:0.5"]},
        "composition": {
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
            "score_transforms": [
                {
                    "name": "score_geological",
                    "params": {
                        "profile": {"type": "weierstrass", "seed": 42},
                        "dimension": "AMPLITUDE",
                        "max_deviation": 0.5,
                    },
                }
            ],
        },
    }

    score = parse_composition(json_data)
    assert len(score.voices[0]) == 2
    # Default amplitude is 0.5. After transform, it should be different.
    assert score.voices[0][0].amplitude != 0.5
    assert score.voices[0][1].amplitude != 0.5


@pytest.mark.parametrize(
    "bad_profile_config",
    [
        {"type": "nonexistent"},
        {"type": "weierstrass", "params": {"bad_param": 1}},
        {"params": {}},
    ],
)
def test_parse_composition_with_bad_geological_config_raises_error(bad_profile_config):
    # Ensures user-facing errors from the profile factory are propagated
    # up through the composition parser.
    json_data = {
        "motifs": {"seed": ["440"]},
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["seed"],
                            "transforms": [
                                {
                                    "name": "geological",
                                    "params": {
                                        "profile": bad_profile_config,
                                        "dimension": "FREQUENCY",
                                        "max_deviation": 0.1,
                                    },
                                }
                            ],
                        }
                    ]
                }
            ]
        },
    }
    with pytest.raises(ValueError):
        parse_composition(json_data)


def test_parse_composition_score_target_motifs_scope_receives_parsed_motifs():
    captured = {}

    def capture_score_target_motifs_transform(score, parsed_motifs, motif):
        captured["motif"] = motif
        captured["parsed_motifs"] = parsed_motifs
        return score

    TRANSFORMS["_test_score_with_motifs"] = TransformDescriptor(
        "_test_score_with_motifs",
        TransformScope.SCORE_TARGET_MOTIFS,
        capture_score_target_motifs_transform,
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    param_type=TransformParamType.STRING,
                    required=True,
                )
            }
        ),
    )

    try:
        parse_composition(
            {
                "motifs": {"seed": ["440:0.5"]},
                "composition": {
                    "voices": [],
                    "score_transforms": [
                        {
                            "name": "_test_score_with_motifs",
                            "params": {"motif": "seed"},
                        }
                    ],
                },
            }
        )
    finally:
        TRANSFORMS.pop("_test_score_with_motifs", None)

    assert captured["motif"] == "seed"
    assert captured["parsed_motifs"]["seed"][0].frequency == 440.0
    assert captured["parsed_motifs"]["seed"][0].duration == 0.5


def test_parse_composition_score_target_motifs_scope_requires_params_object():
    def noop_score_target_motifs_transform(score, parsed_motifs, motif):
        return score

    TRANSFORMS["_test_score_with_motifs"] = TransformDescriptor(
        "_test_score_with_motifs",
        TransformScope.SCORE_TARGET_MOTIFS,
        noop_score_target_motifs_transform,
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    param_type=TransformParamType.STRING,
                    required=True,
                )
            }
        ),
    )

    try:
        invalid_raw_scalar_param = 1.0
        with pytest.raises(ValueError):
            parse_composition(
                {
                    "motifs": {"seed": ["440:0.5"]},
                    "composition": {
                        "voices": [],
                        "score_transforms": [
                            {
                                "name": "_test_score_with_motifs",
                                "params": invalid_raw_scalar_param,
                            }
                        ],
                    },
                }
            )
    finally:
        TRANSFORMS.pop("_test_score_with_motifs", None)


def test_parse_composition_score_target_motifs_scope_requires_params():
    def noop_score_target_motifs_transform(score, parsed_motifs, motif):
        return score

    TRANSFORMS["_test_score_with_motifs"] = TransformDescriptor(
        "_test_score_with_motifs",
        TransformScope.SCORE_TARGET_MOTIFS,
        noop_score_target_motifs_transform,
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    param_type=TransformParamType.STRING,
                    required=True,
                )
            }
        ),
    )

    try:
        with pytest.raises(ValueError):
            parse_composition(
                {
                    "motifs": {"seed": ["440:0.5"]},
                    "composition": {
                        "voices": [],
                        "score_transforms": [{"name": "_test_score_with_motifs"}],
                    },
                }
            )
    finally:
        TRANSFORMS.pop("_test_score_with_motifs", None)


def test_stretto_with_missing_required_fields_raises_error():
    descriptor = TRANSFORMS["stretto"]
    valid_params = {
        "motif": "subject",
        "num_times": 2,
        "spacing": "golden_ratio",
    }

    for required_field in descriptor.params_spec.required_fields:
        incomplete_params = valid_params.copy()
        incomplete_params.pop(required_field)
        composition_doc = {
            "motifs": {"subject": ["440:0.5"]},
            "composition": {
                "voices": [],
                "score_transforms": [{"name": "stretto", "params": incomplete_params}],
            },
        }

        with pytest.raises(ValueError):
            parse_composition(composition_doc)
