import pytest

from composition.parser import (
    _create_voice_plans_from_document,
    _validate_composition_document,
    generate_score_plan,
)
from composition.schema import CompositionDocumentInput
from composition.transformer import transform_score
from score_model.motif import Motif
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones


class TestAccelerandoParserIntegration:
    """Tests that accelerando can be invoked from composition JSON."""

    def test_accelerando_with_preset_params(self):
        composition: CompositionDocumentInput = {
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
        composition: CompositionDocumentInput = {
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
        composition: CompositionDocumentInput = {
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
        composition: CompositionDocumentInput = {
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
        composition: CompositionDocumentInput = {
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
        composition: CompositionDocumentInput = {
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


def test_validate_composition_document_returns_validated_document():
    composition_document: CompositionDocumentInput = {
        "motifs": {"seed": ["440"]},
        "composition": {
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
            "score_transforms": [{"name": "reverse"}],
        },
    }

    validated_document = _validate_composition_document(composition_document)

    default_for_missing_transforms = []
    default_for_missing_params = {}

    assert validated_document == {
        "motifs": {"seed": ["440"]},
        "composition": {
            "voices": [{"phrases": [{"motifs": ["seed"], "transforms": default_for_missing_transforms}]}],
            "score_transforms": [{"name": "reverse", "params": default_for_missing_params}],
        },
    }


def test_validate_composition_document_defaults_missing_phrase_transforms():
    composition_document: CompositionDocumentInput = {
        "motifs": {"seed": ["440"]},
        "composition": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["composition"]["voices"][0]["phrases"][0]["transforms"] == []


def test_validate_composition_document_defaults_missing_score_transforms():
    composition_document: CompositionDocumentInput = {
        "motifs": {"seed": ["440"]},
        "composition": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["composition"]["score_transforms"] == []


def test_validate_composition_document_rejects_non_object():
    with pytest.raises(ValueError):
        _validate_composition_document("not-an-object")


def test_validate_composition_document_rejects_missing_motifs():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
            }
        )


def test_validate_composition_document_rejects_missing_composition():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
            }
        )


def test_validate_composition_document_rejects_missing_voices():
    composition_document: CompositionDocumentInput = {
        "motifs": {"seed": ["440"]},
        "composition": {"score_transforms": [{"name": "reverse"}]},
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["composition"]["voices"] == []


def test_validate_composition_document_rejects_empty_composition():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {},
            }
        )


def test_validate_composition_document_allows_empty_voices():
    composition_document: CompositionDocumentInput = {
        "motifs": {"seed": ["440"]},
        "composition": {"voices": []},
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["composition"]["voices"] == []


def test_validate_composition_document_rejects_non_string_motif_definition_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {1: ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
            }
        )


def test_validate_composition_document_rejects_non_list_motif_definition_value():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": "440"},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
            }
        )


def test_validate_composition_document_rejects_non_string_tone_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": [440]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
            }
        )


def test_validate_composition_document_rejects_empty_tone_string():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": [""]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
            }
        )


def test_validate_composition_document_rejects_non_object_voice_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": ["not-an-object"]},
            }
        )


def test_validate_composition_document_rejects_voice_with_non_list_phrases():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": "not-a-list"}]},
            }
        )


def test_validate_composition_document_rejects_non_object_phrase_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": ["not-an-object"]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_with_non_list_motifs():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": "not-a-list"}]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_with_empty_motifs_list():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": []}]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_with_non_string_motif_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": [1]}]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_with_empty_motif_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": [""]}]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_with_non_list_transforms():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"], "transforms": {}}]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_transform_without_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"], "transforms": [{}]}]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_transform_with_non_string_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"voices": [{"phrases": [{"motifs": ["seed"], "transforms": [{"name": 1}]}]}]},
            }
        )


def test_validate_composition_document_rejects_phrase_transform_with_non_object_params():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {
                    "voices": [{"phrases": [{"motifs": ["seed"], "transforms": [{"name": "reverse", "params": []}]}]}]
                },
            }
        )


def test_validate_composition_document_rejects_non_object_score_transform_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": ["not-an-object"]},
            }
        )


def test_validate_composition_document_rejects_score_transform_without_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": [{}]},
            }
        )


def test_validate_composition_document_rejects_score_transform_with_non_string_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": [{"name": 1}]},
            }
        )


def test_validate_composition_document_rejects_score_transform_with_non_object_params():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "motifs": {"seed": ["440"]},
                "composition": {"score_transforms": [{"name": "reverse", "params": []}]},
            }
        )


def test_create_voice_plans_rejects_unknown_motif_name():
    with pytest.raises(ValueError):
        _create_voice_plans_from_document(
            voices_section=[{"phrases": [{"motifs": ["unknown"]}]}],
            plan_motifs={"known": Motif(name="known", tones=[Tone(440.0)])},
        )
