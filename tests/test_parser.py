import pytest

from composition.parser import (
    _create_voice_plans_from_document,
    _extract_composition_sections,
    _extract_phrase_transform_requests,
    _extract_requests_from_phrase,
    _extract_requests_from_voice,
    _validate_composition_structure,
    _validate_and_extract_motifs,
    generate_score_plan,
)
from composition.schema import CompositionDocument
from composition.transformer import transform_score
from score_model.motif import Motif
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones


class TestAccelerandoParserIntegration:
    """Tests that accelerando can be invoked from composition JSON."""

    def test_accelerando_with_preset_params(self):
        composition: CompositionDocument = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "accelerando",
                                        "params": {
                                            "strength": "high",
                                            "jaggedness": "low"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3

        # Accelerando should decrease durations across the phrase
        assert tones[0].duration > tones[1].duration
        assert tones[1].duration > tones[2].duration

    def test_accelerando_with_numeric_params(self):
        composition: CompositionDocument = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "accelerando",
                                        "params": {
                                            "strength": 0.75,
                                            "jaggedness": 0.0
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3
        assert tones[0].duration > tones[2].duration

    def test_accelerando_preserves_frequencies(self):
        composition: CompositionDocument = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "accelerando",
                                        "params": {
                                            "strength": "medium",
                                            "jaggedness": "none"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert tones[0].frequency == 440
        assert tones[1].frequency == 494
        assert tones[2].frequency == 523


class TestRitardandoParserIntegration:
    """Tests that ritardando can be invoked from composition JSON."""

    def test_ritardando_with_preset_params(self):
        composition: CompositionDocument = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "ritardando",
                                        "params": {
                                            "strength": "high",
                                            "jaggedness": "low"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3

        # Ritardando should increase durations across the phrase
        assert tones[0].duration < tones[1].duration
        assert tones[1].duration < tones[2].duration

    def test_ritardando_with_numeric_params(self):
        composition: CompositionDocument = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "ritardando",
                                        "params": {
                                            "strength": 0.75,
                                            "jaggedness": 0.0
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3
        assert tones[0].duration < tones[2].duration

    def test_ritardando_preserves_frequencies(self):
        composition: CompositionDocument = {
            "motifs": {
                "theme": ["440:0.5", "494:0.5", "523:0.5"]
            },
            "composition": {
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["theme"],
                                "transforms": [
                                    {
                                        "name": "ritardando",
                                        "params": {
                                            "strength": "medium",
                                            "jaggedness": "none"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert tones[0].frequency == 440
        assert tones[1].frequency == 494
        assert tones[2].frequency == 523


def test_validate_and_extract_motifs_rejects_non_dict_phrase_config():
    with pytest.raises(ValueError):
        _validate_and_extract_motifs(["not", "a", "dict"])


def test_validate_composition_structure_returns_validated_document():
    composition_document: CompositionDocument = {
        "motifs": {"seed": ["440"]},
        "composition": {
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
            "score_transforms": [{"name": "reverse"}],
        },
    }

    validated_document = _validate_composition_structure(composition_document)

    assert validated_document == composition_document


def test_validate_composition_structure_rejects_non_object():
    with pytest.raises(ValueError):
        _validate_composition_structure("not-an-object")  # type: ignore[arg-type]


def test_validate_composition_structure_rejects_non_string_motif_definition_name():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {1: ["440"]},
                "composition": {"voices": []},
            }
        )


def test_validate_composition_structure_rejects_non_list_motif_definition_value():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": "440"},
                "composition": {"voices": []},
            }
        )


def test_validate_composition_structure_rejects_non_string_tone_entry():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": [440]},
                "composition": {"voices": []},
            }
        )


def test_validate_composition_structure_rejects_empty_tone_string():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": [""]},
                "composition": {"voices": []},
            }
        )


def test_validate_composition_structure_rejects_non_object_voice_entry():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": ["not-an-object"]},
            }
        )


def test_validate_composition_structure_rejects_voice_with_non_list_phrases():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": "not-a-list"}]},
            }
        )


def test_validate_composition_structure_rejects_non_object_phrase_entry():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": ["not-an-object"]}]},
            }
        )


def test_validate_composition_structure_rejects_phrase_with_non_list_motifs():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": "not-a-list"}]}]},
            }
        )


def test_validate_composition_structure_rejects_phrase_with_non_string_motif_entry():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": [1]}]}]},
            }
        )


def test_validate_composition_structure_rejects_phrase_with_empty_motif_name():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": [""]}]}]},
            }
        )


def test_validate_composition_structure_rejects_phrase_with_non_list_transforms():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"], "transforms": {}}]}]},
            }
        )


def test_validate_composition_structure_rejects_phrase_transform_without_name():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"], "transforms": [{}]}]}]},
            }
        )


def test_validate_composition_structure_rejects_phrase_transform_with_non_string_name():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"], "transforms": [{"name": 1}]}]}]},
            }
        )


def test_validate_composition_structure_rejects_phrase_transform_with_non_object_params():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"], "transforms": [{"name": "reverse", "params": []}]}]}]
                },
            }
        )


def test_validate_composition_structure_rejects_non_object_score_transform_entry():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": ["not-an-object"]},
            }
        )


def test_validate_composition_structure_rejects_score_transform_without_name():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": [{}]},
            }
        )


def test_validate_composition_structure_rejects_score_transform_with_non_string_name():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": [{"name": 1}]},
            }
        )


def test_validate_composition_structure_rejects_score_transform_with_non_object_params():
    with pytest.raises(ValueError):
        _validate_composition_structure(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": [{"name": "reverse", "params": []}]},
            }
        )


def test_extract_composition_sections_returns_expected_sections():
    motifs_section, voices_section, score_transforms_section = _extract_composition_sections(
        {
            "motifs": {"seed": ["440"]},
            "composition": {
                "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                "score_transforms": [{"name": "reverse"}],
            },
        }
    )

    assert motifs_section == {"seed": ["440"]}
    assert voices_section == [{"phrases": [{"motifs": ["seed"]}]}]
    assert score_transforms_section == [{"name": "reverse"}]


def test_extract_requests_from_phrase_rejects_non_dict_phrase():
    with pytest.raises(ValueError):
        _extract_requests_from_phrase([], voice_index=0, phrase_index=0)


def test_extract_requests_from_phrase_rejects_non_list_transforms_field():
    with pytest.raises(ValueError):
        _extract_requests_from_phrase({"motifs": ["seed"], "transforms": {}}, voice_index=0, phrase_index=0)


def test_extract_requests_from_voice_rejects_non_dict_voice():
    with pytest.raises(ValueError):
        _extract_requests_from_voice([], voice_index=0)


def test_extract_requests_from_voice_rejects_non_list_phrases_field():
    with pytest.raises(ValueError):
        _extract_requests_from_voice({"phrases": {}}, voice_index=0)


def test_create_voice_plans_rejects_unknown_motif_name():
    with pytest.raises(ValueError):
        _create_voice_plans_from_document(
            voices_section=[{"phrases": [{"motifs": ["unknown"]}]}],
            plan_motifs={"known": Motif(name="known", tones=[Tone(440.0)])},
        )

def test_extract_composition_sections_defaults_missing_sections():
    motifs_section, voices_section, score_transforms_section = _extract_composition_sections(
        {}
    )

    assert motifs_section == {}
    assert voices_section == []
    assert score_transforms_section == []
