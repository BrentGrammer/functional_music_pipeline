import pytest

from composition.parser import (
    _create_voice_plans_from_document,
    _validate_composition_document,
    generate_score_plan,
)
from composition.schema import CompositionDocumentInput, TransformConfig
from composition.transformer import transform_score
from score_model.motif import Motif
from score_model.tone import Tone
from score_model.traversal import flatten_voice_tones


class TestAccelerandoParserIntegration:
    """Tests that accelerando can be invoked from composition JSON."""

    def test_accelerando_with_preset_params(self):
        composition: CompositionDocumentInput = {
            "name": "Accelerando Preset",
            "score": {
                "motifs": {
                    "theme": ["440:0.5", "494:0.5", "523:0.5"],
                },
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
                                            "jaggedness": "low",
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3
        assert tones[0].duration > tones[1].duration
        assert tones[1].duration > tones[2].duration

    def test_accelerando_with_numeric_params(self):
        composition: CompositionDocumentInput = {
            "name": "Accelerando Numeric",
            "score": {
                "motifs": {
                    "theme": ["440:0.5", "494:0.5", "523:0.5"],
                },
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
                                            "jaggedness": 0.0,
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3
        assert tones[0].duration > tones[2].duration

    def test_accelerando_preserves_frequencies(self):
        composition: CompositionDocumentInput = {
            "name": "Accelerando Frequencies",
            "score": {
                "motifs": {
                    "theme": ["440:0.5", "494:0.5", "523:0.5"],
                },
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
                                            "jaggedness": "none",
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ],
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
            "name": "Ritardando Preset",
            "score": {
                "motifs": {
                    "theme": ["440:0.5", "494:0.5", "523:0.5"],
                },
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
                                            "jaggedness": "low",
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3
        assert tones[0].duration < tones[1].duration
        assert tones[1].duration < tones[2].duration

    def test_ritardando_with_numeric_params(self):
        composition: CompositionDocumentInput = {
            "name": "Ritardando Numeric",
            "score": {
                "motifs": {
                    "theme": ["440:0.5", "494:0.5", "523:0.5"],
                },
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
                                            "jaggedness": 0.0,
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert len(tones) == 3
        assert tones[0].duration < tones[2].duration

    def test_ritardando_preserves_frequencies(self):
        composition: CompositionDocumentInput = {
            "name": "Ritardando Frequencies",
            "score": {
                "motifs": {
                    "theme": ["440:0.5", "494:0.5", "523:0.5"],
                },
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
                                            "jaggedness": "none",
                                        },
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        }

        score = transform_score(generate_score_plan(composition))
        tones = flatten_voice_tones(score.voices[0])

        assert tones[0].frequency == 440
        assert tones[1].frequency == 494
        assert tones[2].frequency == 523


def test_validate_composition_document_returns_validated_document():
    composition_document: CompositionDocumentInput = {
        "name": "Document Study",
        "description": "Parser validation example.",
        "document_version": 1,
        "score": {
            "motifs": {"seed": ["440"]},
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
            "score_transforms": [{"name": "reverse"}],
        }
    }

    validated_document = _validate_composition_document(composition_document)

    default_for_missing_transforms: list[TransformConfig] = []
    default_for_missing_params: dict[str, object] = {}

    assert validated_document == {
        "name": "Document Study",
        "description": "Parser validation example.",
        "document_version": 1,
        "score": {
            "motifs": {"seed": ["440"]},
            "voices": [{"phrases": [{"motifs": ["seed"], "transforms": default_for_missing_transforms}]}],
            "score_transforms": [{"name": "reverse", "params": default_for_missing_params}],
        }
    }


def test_validate_composition_document_defaults_missing_phrase_transforms():
    composition_document: CompositionDocumentInput = {
        "name": "Default Phrase Transforms",
        "score": {
            "motifs": {"seed": ["440"]},
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
        }
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["document_version"] == 1
    assert validated_document["score"]["voices"][0]["phrases"][0]["transforms"] == []


def test_validate_composition_document_defaults_missing_score_transforms():
    composition_document: CompositionDocumentInput = {
        "name": "Default Score Transforms",
        "score": {
            "motifs": {"seed": ["440"]},
            "voices": [{"phrases": [{"motifs": ["seed"]}]}],
        }
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["document_version"] == 1
    assert validated_document["score"]["score_transforms"] == []


def test_validate_composition_document_rejects_non_object():
    with pytest.raises(ValueError):
        _validate_composition_document("not-an-object")


def test_validate_composition_document_rejects_empty_name():
    with pytest.raises(ValueError):
        _validate_composition_document({"name": "", "score": {"motifs": {}, "voices": []}})


def test_validate_composition_document_rejects_missing_name():
    with pytest.raises(ValueError):
        _validate_composition_document({"score": {"motifs": {}, "voices": []}})


def test_validate_composition_document_rejects_non_string_description():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {"name": "Description Study", "description": 123, "score": {"motifs": {}, "voices": []}}
        )


def test_validate_composition_document_rejects_non_integer_document_version():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {"name": "Version Study", "document_version": "1", "score": {"motifs": {}, "voices": []}}
        )


def test_validate_composition_document_rejects_boolean_document_version():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {"name": "Version Study", "document_version": True, "score": {"motifs": {}, "voices": []}}
        )


def test_validate_composition_document_rejects_missing_motifs():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "name": "Missing Motifs",
                "score": {"voices": [{"phrases": [{"motifs": ["seed"]}]}]},
            }
        )


def test_validate_composition_document_rejects_missing_score():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "name": "Missing Score",
                "motifs": {"seed": ["440"]},
            }
        )


def test_validate_composition_document_rejects_missing_voices():
    composition_document: CompositionDocumentInput = {
        "name": "Missing Voices",
        "score": {
            "motifs": {"seed": ["440"]},
            "score_transforms": [{"name": "reverse"}],
        }
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["score"]["voices"] == []


def test_validate_composition_document_rejects_empty_score():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "name": "Empty Score",
                "score": {},
            }
        )


def test_validate_composition_document_allows_empty_voices():
    composition_document: CompositionDocumentInput = {
        "name": "Empty Voices",
        "score": {
            "motifs": {"seed": ["440"]},
            "voices": [],
        }
    }

    validated_document = _validate_composition_document(composition_document)

    assert validated_document["score"]["voices"] == []


def test_validate_composition_document_rejects_non_string_motif_definition_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {1: ["440"]},
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                }
            }
        )


def test_validate_composition_document_rejects_non_list_motif_definition_value():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": "440"},
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                }
            }
        )


def test_validate_composition_document_rejects_non_string_tone_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": [440]},
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                }
            }
        )


def test_validate_composition_document_rejects_empty_tone_string():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": [""]},
                    "voices": [{"phrases": [{"motifs": ["seed"]}]}],
                }
            }
        )


def test_validate_composition_document_rejects_non_object_voice_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": ["not-an-object"],
                }
            }
        )


def test_validate_composition_document_rejects_voice_with_non_list_phrases():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": "not-a-list"}],
                }
            }
        )


def test_validate_composition_document_rejects_non_object_phrase_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": ["not-an-object"]}],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_with_non_list_motifs():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": [{"motifs": "not-a-list"}]}],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_with_empty_motifs_list():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": [{"motifs": []}]}],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_with_non_string_motif_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": [{"motifs": [1]}]}],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_with_empty_motif_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": [{"motifs": [""]}]}],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_with_non_list_transforms():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": [{"motifs": ["seed"], "transforms": {}}]}],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_transform_without_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [{"phrases": [{"motifs": ["seed"], "transforms": [{}]}]}],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_transform_with_non_string_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [
                        {"phrases": [{"motifs": ["seed"], "transforms": [{"name": 1}]}]}
                    ],
                }
            }
        )


def test_validate_composition_document_rejects_phrase_transform_with_non_object_params():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "voices": [
                        {
                            "phrases": [
                                {"motifs": ["seed"], "transforms": [{"name": "reverse", "params": []}]}
                            ]
                        }
                    ],
                }
            }
        )


def test_validate_composition_document_rejects_non_object_score_transform_entry():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "score_transforms": ["not-an-object"],
                }
            }
        )


def test_validate_composition_document_rejects_score_transform_without_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "score_transforms": [{}],
                }
            }
        )


def test_validate_composition_document_rejects_score_transform_with_non_string_name():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "score_transforms": [{"name": 1}],
                }
            }
        )


def test_validate_composition_document_rejects_score_transform_with_non_object_params():
    with pytest.raises(ValueError):
        _validate_composition_document(
            {
                "score": {
                    "motifs": {"seed": ["440"]},
                    "score_transforms": [{"name": "reverse", "params": []}],
                }
            }
        )


def test_create_voice_plans_rejects_unknown_motif_name():
    with pytest.raises(ValueError):
        _create_voice_plans_from_document(
            voices_section=[{"phrases": [{"motifs": ["unknown"], "transforms": []}]}],
            plan_motifs={"known": Motif(name="known", tones=[Tone(440.0)])},
        )
