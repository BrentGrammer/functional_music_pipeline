import pytest

from composition.parser import (
    generate_score_plan,
    parse_motifs,
)
from composition.schema import PhraseConfig
from composition.transformer import transform_score
from score_model.math_constants import FEIGENBAUM_DELTA, GOLDEN_RATIO
from score_model.score import Score
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones
from transforms.base import (
    EnumParam,
    ScoreTransformDefinition,
    StringParam,
    TransformParamFieldSpec,
    TransformParamsSpec,
)
from transforms.registry import PHRASE_TRANSFORMS, SCORE_TRANSFORMS


def render_phrase_from_config(phrase_config: object, parsed_motifs: dict[str, list[Tone]], reference_tones: list[Tone] | None = None) -> list[Tone]:
    motifs_section: dict[str, list[str]] = {
        name: [f"{tone.frequency}:{tone.duration}" for tone in tones]
        for name, tones in parsed_motifs.items()
    }

    composition_voices: list[dict[str, object]] = []
    if reference_tones is not None:
        motifs_section["__reference__"] = [f"{tone.frequency}:{tone.duration}" for tone in reference_tones]
        composition_voices.append({"phrases": [{"motifs": ["__reference__"]}]})
    composition_voices.append({"phrases": [phrase_config]})

    composition_doc = {
        "motifs": motifs_section,
        "composition": {"voices": composition_voices},
    }
    score = transform_score(generate_score_plan(composition_doc))
    return flatten_voice_tones(score.voices[-1])


def test_stretto_spacing_descriptor_accepts_named_or_float_spacing():
    spacing_spec = SCORE_TRANSFORMS["stretto"].params_spec.fields["spacing"]

    assert isinstance(spacing_spec.schema, tuple)
    assert spacing_spec.required is True
    assert isinstance(spacing_spec.schema[0], EnumParam)
    assert spacing_spec.schema[0].allowed_values == ("golden_ratio", "feigenbaum_delta")


@pytest.mark.parametrize("transform_name", ["accelerando", "ritardando"])
def test_tempo_curve_descriptor_accepts_preset_or_float_controls(transform_name):
    fields = PHRASE_TRANSFORMS[transform_name].params_spec.fields

    assert isinstance(fields["strength"].schema, tuple)
    assert fields["strength"].required is True
    assert isinstance(fields["strength"].schema[0], EnumParam)
    assert fields["strength"].schema[0].allowed_values == ("none", "low", "medium", "high", "extreme")
    assert isinstance(fields["jaggedness"].schema, tuple)
    assert fields["jaggedness"].required is False
    assert isinstance(fields["jaggedness"].schema[0], EnumParam)
    assert fields["jaggedness"].schema[0].allowed_values == ("none", "low", "medium", "high", "extreme")


def test_fixed_string_descriptors_use_enum_metadata():
    position_spec = PHRASE_TRANSFORMS["pad_silence"].params_spec.fields["position"]

    assert isinstance(position_spec.schema, EnumParam)
    assert position_spec.schema.allowed_values == ("start", "end")


@pytest.mark.parametrize(
    ("transform_name", "params"),
    [
        ("delay", {"seconds": True}),
        ("delay", {"seconds": "slow"}),
        ("repeat", {"count": True}),
        ("repeat", {"count": 1.5}),
    ],
)
def test_phrase_transform_params_reject_invalid_basic_types(transform_name, params):
    parsed_motifs = {"seed": [Tone(440)]}
    phrase_config = {
        "motifs": ["seed"],
        "transforms": [{"name": transform_name, "params": params}],
    }

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_config, parsed_motifs)


def test_phrase_transform_params_reject_unknown_enum_value():
    parsed_motifs = {"seed": [Tone(440)]}
    phrase_config = {
        "motifs": ["seed"],
        "transforms": [
            {
                "name": "pad_silence",
                "params": {"seconds": 0.5, "position": "middle"},
            }
        ],
    }

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_config, parsed_motifs)


@pytest.mark.parametrize(
    "strength",
    ["high", 0.75],
)
def test_union_transform_params_accept_enum_or_float_values(strength):
    parsed_motifs = {"seed": [Tone(440, 0.5), Tone(660, 0.5)]}
    phrase_config = {
        "motifs": ["seed"],
        "transforms": [
            {
                "name": "accelerando",
                "params": {"strength": strength, "jaggedness": "none"},
            }
        ],
    }

    result = render_phrase_from_config(phrase_config, parsed_motifs)

    assert len(result) == 2


@pytest.mark.parametrize(
    "strength",
    ["wild", True, []],
)
def test_union_transform_params_reject_values_outside_all_branches(strength):
    parsed_motifs = {"seed": [Tone(440, 0.5), Tone(660, 0.5)]}
    phrase_config = {
        "motifs": ["seed"],
        "transforms": [
            {
                "name": "accelerando",
                "params": {"strength": strength, "jaggedness": "none"},
            }
        ],
    }

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_config, parsed_motifs)


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


def test_parse_motifs_requires_string_keys():
    with pytest.raises(ValueError):
        parse_motifs({1: ["440"]})

def test_parse_phrase_single_motif_from_motifs_list():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5), Tone(880, 0.5)]
    }

    phrase_dict: PhraseConfig = {
        "motifs": ["seed_a"],
        "transforms": [{"name": "reverse"}]
    }

    result = render_phrase_from_config(phrase_dict, parsed_motifs)

    assert len(result) == 2
    assert result[0].frequency == 880.0
    assert result[1].frequency == 440.0

def test_parse_phrase_multiple_motifs():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)],
        "seed_b": [Tone(880, 0.25), Tone(523.25, 0.75)]
    }

    phrase_dict: PhraseConfig = {
        "motifs": ["seed_a", "seed_b"]
    }

    result = render_phrase_from_config(phrase_dict, parsed_motifs)

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

    phrase_dict: PhraseConfig = {
        "motifs": ["seed_a", "seed_b"],
        "transforms": [{"name": "reverse"}]
    }

    result = render_phrase_from_config(phrase_dict, parsed_motifs)

    assert len(result) == 3
    assert [tone.frequency for tone in result] == [880.0, 660.0, 440.0]
    assert [tone.duration for tone in result] == [0.75, 0.25, 0.5]

def test_parse_phrase_scale_applies_to_all_grouped_motifs():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)],
        "seed_b": [Tone(880, 0.25), Tone(523.25, 0.75)]
    }

    phrase_dict: PhraseConfig = {
        "motifs": ["seed_a", "seed_b"],
        "transforms": [{"name": "scale", "params": {"dimension": "duration", "factor": 2.0}}]
    }

    result = render_phrase_from_config(phrase_dict, parsed_motifs)

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
    phrase_dict: PhraseConfig = {
        "motifs": ["seed_a"],
        "transforms": [{"name": "delay", "params": {"seconds": DELAY_SECONDS}}],
    }

    result = render_phrase_from_config(phrase_dict, parsed_motifs)

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
        phrase_dict: PhraseConfig = {
            "motifs": ["seed_a"],
            "transforms": [{"name": "scale", "params": {"dimension": "duration", "factor": factor}}],
        }

        result = render_phrase_from_config(phrase_dict, parsed_motifs)

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
        result = render_phrase_from_config(phrase_config, parsed_motifs)
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
        result = render_phrase_from_config(phrase_config, parsed_motifs)
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
            render_phrase_from_config(phrase_config, parsed_motifs)

    def test_scale_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["scale"]
        valid_params = {"dimension": "duration", "factor": 2.0}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "scale", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_score_scale_with_numeric_param_raises_error(self):
        # Ensures the score-level 'scale' transform enforces explicit parameterization.
        composition_doc = {
            "motifs": {"seed": ["440"]},
            "composition": {
                "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                "score_transforms": [{"name": "scale", "params": 2.0}],
            },
        }
        with pytest.raises(ValueError):
            transform_score(generate_score_plan(composition_doc))

    def test_score_scale_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["scale"]
        valid_params = {"dimension": "duration", "factor": 2.0}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "scale", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                transform_score(generate_score_plan(composition_doc))

    def test_transpose_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["transpose"]
        valid_params = {"semitones": 1.0}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "transpose", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_score_transpose_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["transpose"]
        valid_params = {"semitones": 1.0}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "transpose", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                transform_score(generate_score_plan(composition_doc))

    def test_reverse_rejects_unknown_top_level_params(self):
        parsed_motifs = {"seed": [Tone(440)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [{"name": "reverse", "params": {"unexpected": True}}],
        }

        with pytest.raises(ValueError):
            render_phrase_from_config(phrase_config, parsed_motifs)

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
    ) -> None:
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
            render_phrase_from_config(phrase_config, parsed_motifs)

    def test_delay_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["delay"]
        valid_params = {"seconds": 0.25}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "delay", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_score_delay_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["delay"]
        valid_params = {"seconds": 0.25}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "delay", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                transform_score(generate_score_plan(composition_doc))

    def test_repeat_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["repeat"]
        valid_params = {"count": 2}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "repeat", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_score_repeat_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["repeat"]
        valid_params = {"count": 2}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "repeat", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                transform_score(generate_score_plan(composition_doc))

    def test_accelerando_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["accelerando"]
        valid_params = {"strength": "medium", "jaggedness": "none"}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "accelerando", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_ritardando_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["ritardando"]
        valid_params = {"strength": "medium", "jaggedness": "none"}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "ritardando", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_drift_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["drift"]
        valid_params = {"dimension": "frequency", "rate": 0.1}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "drift", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_score_drift_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["drift"]
        valid_params = {"dimension": "frequency", "rate": 0.1}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "drift", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                transform_score(generate_score_plan(composition_doc))

    def test_weierstrass_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["weierstrass"]
        valid_params = {
            "dimension": "frequency",
            "intensity": "medium",
        }

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "weierstrass", "params": incomplete_params}],
            }

            with pytest.raises(ValueError):
                render_phrase_from_config(phrase_config, parsed_motifs)

    def test_score_weierstrass_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["weierstrass"]
        valid_params = {
            "dimension": "frequency",
            "intensity": "medium",
        }

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "weierstrass", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                transform_score(generate_score_plan(composition_doc))

    def test_cellular_automata_with_missing_required_fields_raises_error(self):
        parsed_motifs = {"seed": [Tone(440)]}
        descriptor = PHRASE_TRANSFORMS["cellular_automata"]
        valid_params = {
            "dimension": "frequency",
            "rule": 30,
            "generations": 5,
            "max_deviation": 0.3,
        }

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            phrase_config = {
                "motifs": ["seed"],
                "transforms": [{"name": "cellular_automata", "params": incomplete_params}],
            }

            with pytest.raises(ValueError) as exc_info:
                render_phrase_from_config(phrase_config, parsed_motifs)
            assert str(exc_info.value)

    def test_score_cellular_automata_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["cellular_automata"]
        valid_params = {
            "dimension": "frequency",
            "rule": 30,
            "generations": 5,
            "max_deviation": 0.3,
        }

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                    "score_transforms": [{"name": "cellular_automata", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError) as exc_info:
                transform_score(generate_score_plan(composition_doc))
            assert str(exc_info.value)

    def test_add_pedal_tone_with_missing_required_fields_raises_error(self):
        descriptor = SCORE_TRANSFORMS["add_pedal_tone"]
        valid_params = {"frequency": 130.81}

        for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
            incomplete_params = valid_params.copy()
            incomplete_params.pop(required_field)
            composition_doc = {
                "motifs": {},
                "composition": {
                    "voices": [],
                    "score_transforms": [{"name": "add_pedal_tone", "params": incomplete_params}],
                },
            }

            with pytest.raises(ValueError):
                transform_score(generate_score_plan(composition_doc))

    def test_add_pedal_tone_applies_from_composition_json(self):
        pedal_tone = 330.1
        
        composition_doc = {
            "motifs": {},
            "composition": {
                "voices": [],
                "score_transforms": [
                    {
                        "name": "add_pedal_tone",
                        "params": {"frequency": pedal_tone},
                    }
                ],
            },
        }

        score = transform_score(generate_score_plan(composition_doc))

        assert len(score.voices) == 1
        assert flatten_voice_tones(score.voices[0])[0].frequency == pytest.approx(pedal_tone)

    def test_erosion_accepts_optional_dimension(self):
        parsed_motifs = {"seed": [Tone(440, 0.5), Tone(880, 0.5)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [{"name": "erosion", "params": {"dimension": "amplitude"}}],
        }

        result = render_phrase_from_config(phrase_config, parsed_motifs)
        # Erosion of amplitude should change the amplitude of the second tone.
        assert result[1].amplitude < 1.0

    def test_golden_ratio_accepts_optional_dimension(self):
        parsed_motifs = {"seed": [Tone(440, 1.0)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [{"name": "golden_ratio", "params": {"dimension": "frequency"}}],
        }

        result = render_phrase_from_config(phrase_config, parsed_motifs)
        # golden_ratio on frequency scales frequency by 1/GOLDEN_RATIO
        assert result[0].frequency == pytest.approx(440.0 / GOLDEN_RATIO)

    def test_erosion_rejects_unknown_param(self):
        parsed_motifs = {"seed": [Tone(440)]}
        phrase_config = {
            "motifs": ["seed"],
            "transforms": [{"name": "erosion", "params": {"unexpected": 123}}],
        }

        with pytest.raises(ValueError):
            render_phrase_from_config(phrase_config, parsed_motifs)

def test_parse_phrase_with_reference_transform():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)]
    }
    reference_tones = [Tone(110, 1.0)]

    phrase_dict: PhraseConfig = {
        "motifs": ["seed_a"],
        "transforms": [{"name": "phrase_golden_ratio_grow"}]
    }

    result = render_phrase_from_config(phrase_dict, parsed_motifs, reference_tones)

    assert len(result) == 1
    assert result[0].duration == pytest.approx(1.0 * GOLDEN_RATIO)

def test_parse_phrase_reference_transform_uses_total_grouped_phrase_duration():
    parsed_motifs = {
        "seed_a": [Tone(440, 0.5)],
        "seed_b": [Tone(880, 0.5)]
    }
    reference_tones = [Tone(110, 2.0)]

    phrase_dict: PhraseConfig = {
        "motifs": ["seed_a", "seed_b"],
        "transforms": [{"name": "phrase_golden_ratio_grow"}]
    }

    result = render_phrase_from_config(phrase_dict, parsed_motifs, reference_tones)

    assert len(result) == 2
    expected_total_duration = 2.0 * GOLDEN_RATIO
    actual_total_duration = sum(tone.duration for tone in result)
    assert actual_total_duration == pytest.approx(expected_total_duration)
    assert result[0].duration == pytest.approx(expected_total_duration / 2.0)
    assert result[1].duration == pytest.approx(expected_total_duration / 2.0)

def test_generate_score_plan_multi_motif_phrase_followed_by_phrase_uses_phrase_level_reference():
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
                        {"motifs": ["seed_c"], "transforms": [{"name": "phrase_feigenbaum_shrink"}]}
                    ]
                }
            ]
        }
    }

    score = transform_score(generate_score_plan(json_data))
    voice_tones = flatten_voice_tones(score.voices[0])

    assert len(score.voices) == 1
    assert len(voice_tones) == 3

    assert voice_tones[0].frequency == 440.0
    assert voice_tones[0].duration == 0.5
    assert voice_tones[1].frequency == 660.0
    assert voice_tones[1].duration == 0.5

    expected_third_duration = 1.0 / FEIGENBAUM_DELTA
    assert voice_tones[2].frequency == 880.0
    assert voice_tones[2].duration == pytest.approx(expected_third_duration)


def test_generate_score_plan_phrase_relative_transforms_use_document_order():
    json_data = {
        "motifs": {
            "anchor": ["440:1.0"],
            "response": ["550:1.0"],
            "second_voice": ["660:1.0"],
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["anchor"],
                            "transforms": [
                                {
                                    "name": "scale",
                                    "params": {"dimension": "duration", "factor": 2.0},
                                }
                            ],
                        },
                        {
                            "motifs": ["response"],
                            "transforms": [{"name": "phrase_golden_ratio_grow"}],
                        },
                    ]
                },
                {
                    "phrases": [
                        {
                            "motifs": ["second_voice"],
                            "transforms": [{"name": "phrase_golden_ratio_grow"}],
                        }
                    ]
                },
            ]
        },
    }

    score = transform_score(generate_score_plan(json_data))
    first_voice_tones = flatten_voice_tones(score.voices[0])
    second_voice_tones = flatten_voice_tones(score.voices[1])

    assert first_voice_tones[0].duration == pytest.approx(2.0)
    assert first_voice_tones[1].duration == pytest.approx(2.0 * GOLDEN_RATIO)
    assert second_voice_tones[0].duration == pytest.approx((2.0 + (2.0 * GOLDEN_RATIO)) * GOLDEN_RATIO)


def test_parse_phrase_missing_motifs():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"transforms": [{"name": "reverse"}]}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_empty_motifs():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict: dict[str, object] = {"motifs": []}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_non_list_motifs():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": "seed_a"}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_motifs_entries_must_be_non_empty_strings():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a", ""]}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_unknown_motif():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["missing"]}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_requires_phrase_object():
    parsed_motifs = {"seed_a": [Tone(440)]}

    with pytest.raises(ValueError):
        render_phrase_from_config(["seed_a"], parsed_motifs)

def test_parse_phrase_transforms_must_be_a_list():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a"], "transforms": "reverse"}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_transform_object_requires_name():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a"], "transforms": [{"params": 2.0}]}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_transform_must_be_string_or_object():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict = {"motifs": ["seed_a"], "transforms": [123]}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)

def test_parse_phrase_unknown_transform():
    parsed_motifs = {"seed_a": [Tone(440)]}
    phrase_dict: PhraseConfig = {"motifs": ["seed_a"], "transforms": [{"name": "unknown_transform"}]}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)


def test_parse_phrase_requires_params_object_when_transform_params_are_missing():
    parsed_motifs = {"seed": [Tone(440)]}
    phrase_dict: PhraseConfig = {"motifs": ["seed"], "transforms": [{"name": "scale"}]}

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_dict, parsed_motifs)









def test_generate_score_plan_requires_document_object():
    with pytest.raises(ValueError):
        transform_score(generate_score_plan([]))

def test_generate_score_plan_requires_motifs_object():
    with pytest.raises(ValueError):
        transform_score(generate_score_plan({"motifs": [], "composition": {}}))

def test_generate_score_plan_requires_composition_object():
    with pytest.raises(ValueError):
        transform_score(generate_score_plan({"motifs": {}, "composition": []}))

def test_generate_score_plan_requires_voices_list():
    with pytest.raises(ValueError):
        transform_score(generate_score_plan({"motifs": {}, "composition": {"voices": {}}}))

def test_generate_score_plan_requires_voice_objects():
    with pytest.raises(ValueError):
        transform_score(generate_score_plan({"motifs": {}, "composition": {"voices": ["voice_a"]}}))

def test_generate_score_plan_requires_phrases_list():
    with pytest.raises(ValueError):
        transform_score(generate_score_plan({"motifs": {}, "composition": {"voices": [{"phrases": {}}]}}))

def test_generate_score_plan_score_transforms_must_be_list():
    with pytest.raises(ValueError):
        transform_score(generate_score_plan({"motifs": {}, "composition": {"voices": [], "score_transforms": {}}}))

def test_generate_score_plan_score_transform_object_requires_name():
    json_data = {
        "motifs": {},
        "composition": {
            "voices": [],
            "score_transforms": [{"params": 2.0}]
        }
    }

    with pytest.raises(ValueError):
        transform_score(generate_score_plan(json_data))

def test_generate_score_plan_unknown_score_transform():
    json_data = {
        "motifs": {},
        "composition": {
            "voices": [],
            "score_transforms": [{"name": "unknown"}]
        }
    }

    with pytest.raises(ValueError):
        transform_score(generate_score_plan(json_data))


def test_generate_score_plan_rejects_phrase_transform_in_score_transforms():
    json_data = {
        "motifs": {"seed": ["440:0.5", "660:0.5"]},
        "composition": {
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
            "score_transforms": [{"name": "accelerando"}],
        },
    }

    with pytest.raises(ValueError):
        transform_score(generate_score_plan(json_data))


def test_parse_phrase_rejects_score_transform_in_phrase_transforms():
    parsed_motifs = {"seed": [Tone(440.0, duration=0.5)]}
    phrase_config = {
        "motifs": ["seed"],
        "transforms": [{"name": "add_pedal_tone"}],
    }

    with pytest.raises(ValueError):
        render_phrase_from_config(phrase_config, parsed_motifs)


def test_generate_score_plan_score_reverse_applies_to_all_voices_without_params():
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
            "score_transforms": [{"name": "reverse"}],
        },
    }

    score = transform_score(generate_score_plan(json_data))

    assert [tone.frequency for tone in flatten_voice_tones(score.voices[0])] == [660.0, 440.0]
    assert [tone.duration for tone in flatten_voice_tones(score.voices[0])] == [0.25, 0.5]
    assert [tone.frequency for tone in flatten_voice_tones(score.voices[1])] == [990.0, 880.0]
    assert [tone.duration for tone in flatten_voice_tones(score.voices[1])] == [1.0, 0.75]

def test_generate_score_plan_full_score_path():
    json_data = {
        "motifs": {
            "seed_a": ["440:0.5"],
            "seed_b": ["880:0.5"]
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {"motifs": ["seed_a"], "transforms": [{"name": "reverse"}]}
                    ]
                },
                {
                    "phrases": [
                        {"motifs": ["seed_b"], "transforms": []}
                    ]
                }
            ],
            "score_transforms": [{"name": "feigenbaum_sequence"}]
        }
    }

    score = transform_score(generate_score_plan(json_data))

    assert isinstance(score, Score)
    assert len(score.voices) == 2
    voice_0_tones = flatten_voice_tones(score.voices[0])
    voice_1_tones = flatten_voice_tones(score.voices[1])
    assert len(voice_0_tones) == 1
    assert len(voice_1_tones) == 1

    assert voice_0_tones[0].frequency == 440.0
    assert voice_0_tones[0].duration == 0.5

    assert voice_1_tones[0].frequency == 880.0
    assert voice_1_tones[0].duration == pytest.approx(0.5 / FEIGENBAUM_DELTA)

def test_generate_score_plan_with_value_score_transform():
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
                {"name": "scale", "params": {"dimension": "duration", "factor": factor}}
            ]
        }
    }

    score = transform_score(generate_score_plan(json_data))

    assert len(score.voices) == 1
    assert flatten_voice_tones(score.voices[0])[0].duration == original_duration * factor

def test_generate_score_plan_score_target_motifs_scope_receives_score_and_params_only():
    captured = {}

    def capture_score_target_motifs_transform(score, motif):
        captured["motif"] = motif
        captured["score"] = score
        return score

    SCORE_TRANSFORMS["_test_score_with_motifs"] = ScoreTransformDefinition(
        name="_test_score_with_motifs",
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    schema=StringParam(),
                    required=True,
                )
            }
        ),
        transform=lambda score, params: capture_score_target_motifs_transform(score, params["motif"]),
    )
    try:
        transform_score(generate_score_plan(
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
        ))
    finally:
        SCORE_TRANSFORMS.pop("_test_score_with_motifs", None)

    assert captured["motif"] == "seed"
    assert isinstance(captured["score"], Score)


def test_generate_score_plan_score_target_motifs_scope_requires_params_object():
    def noop_score_target_motifs_transform(score, motif):
        return score

    SCORE_TRANSFORMS["_test_score_with_motifs"] = ScoreTransformDefinition(
        name="_test_score_with_motifs",
        transform=lambda score, params: noop_score_target_motifs_transform(score, params["motif"]),
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    schema=StringParam(),
                    required=True,
                )
            }
        ),
    )
    try:
        invalid_raw_scalar_param = 1.0
        with pytest.raises(ValueError):
            transform_score(generate_score_plan(
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
            ))
    finally:
        SCORE_TRANSFORMS.pop("_test_score_with_motifs", None)


def test_generate_score_plan_score_target_motifs_scope_requires_params():
    def noop_score_target_motifs_transform(score, motif):
        return score

    SCORE_TRANSFORMS["_test_score_with_motifs"] = ScoreTransformDefinition(
        name="_test_score_with_motifs",
        transform=lambda score, params: noop_score_target_motifs_transform(score, params["motif"]),
        params_spec=TransformParamsSpec(
            fields={
                "motif": TransformParamFieldSpec(
                    schema=StringParam(),
                    required=True,
                )
            }
        ),
    )
    try:
        with pytest.raises(ValueError):
            transform_score(generate_score_plan(
                {
                    "motifs": {"seed": ["440:0.5"]},
                    "composition": {
                        "voices": [],
                        "score_transforms": [{"name": "_test_score_with_motifs"}],
                    },
                }
            ))
    finally:
        SCORE_TRANSFORMS.pop("_test_score_with_motifs", None)


def test_stretto_with_missing_required_fields_raises_error():
    descriptor = SCORE_TRANSFORMS["stretto"]
    valid_params = {
        "motif": "subject",
        "num_times": 2,
        "spacing": "golden_ratio",
    }

    for required_field in (f for f, s in descriptor.params_spec.fields.items() if s.required):
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
            transform_score(generate_score_plan(composition_doc))
