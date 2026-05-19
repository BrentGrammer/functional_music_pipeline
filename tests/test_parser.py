from composition.parser import generate_score_plan
from composition.schema import CompositionDocument
from composition.transformer import transform_score
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

import pytest

from composition.parser import (
    _apply_phrase_transform_spec,
    _create_voice_plans_from_document,
    _extract_composition_sections,
    _extract_requests_from_phrase,
    _extract_requests_from_voice,
    _validate_and_extract_motifs,
)
from score_model.motif import Motif
from score_model.tone import Tone
from transforms.base import ScoreTransformDefinition, TransformParamsSpec


def test_validate_and_extract_motifs_rejects_non_dict_phrase_config():
    with pytest.raises(ValueError):
        _validate_and_extract_motifs(["not", "a", "dict"])


def test_extract_composition_sections_rejects_invalid_shapes():
    with pytest.raises(ValueError):
        _extract_composition_sections(
            {
                "motifs": "not-a-dict",
                "composition": {
                    "voices": "not-a-list",
                    "score_transforms": "not-a-list",
                },
            }
        )


def test_extract_composition_sections_rejects_non_object():
    with pytest.raises(ValueError):
        _extract_composition_sections("not-an-object")


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


def test_apply_phrase_transform_spec_rejects_non_phrase_transform_definition():
    non_phrase_definition = ScoreTransformDefinition(
        name="not_phrase",
        params_spec=TransformParamsSpec(),
        transform=lambda score, params: score,
    )

    with pytest.raises(ValueError):
        _apply_phrase_transform_spec(
            non_phrase_definition,
            phrase_tones=[Tone(440.0)],
            transform_params={},
            reference_tones=[],
        )


def test_create_voice_plans_rejects_unknown_motif_name():
    with pytest.raises(ValueError):
        _create_voice_plans_from_document(
            voices_section=[{"phrases": [{"motifs": ["unknown"]}]}],
            plan_motifs={"known": Motif(name="known", tones=[Tone(440.0)])},
        )

def test_extract_composition_sections_rejects_non_object_composition_field():
    with pytest.raises(ValueError):
        _extract_composition_sections(
            {
                "motifs": {"seed": ["440"]},
                "composition": "not-an-object",
            }
        )
