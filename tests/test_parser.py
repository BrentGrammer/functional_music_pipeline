import pytest

from composition.parser import (
    _create_voice_plans_from_document,
    _extract_composition_sections,
    _extract_phrase_transform_requests,
    _extract_requests_from_phrase,
    _extract_requests_from_voice,
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
        _extract_composition_sections("not-an-object") # type: ignore[arg-type]


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

def test_extract_composition_sections_rejects_non_object_composition_field():
    with pytest.raises(ValueError):
        _extract_composition_sections(
            {
                "motifs": {"seed": ["440"]},
                "composition": "not-an-object",
            }
        )


def test_extract_composition_sections_rejects_invalid_motifs_after_initial_validation():
    class FlakyDocument(dict):
        def __init__(self):
            super().__init__()
            self._motifs_call_count = 0
            self._composition: object = {"voices": [], "score_transforms": []}

        def get(self, key, default=None):
            if key == "motifs":
                self._motifs_call_count += 1
                return {} if self._motifs_call_count == 1 else "not-a-dict"
            if key == "composition":
                return self._composition
            return super().get(key, default)

    with pytest.raises(ValueError):
        _extract_composition_sections(FlakyDocument())


def test_extract_composition_sections_rejects_invalid_composition_after_initial_validation():
    class FlakyDocument(dict):
        def __init__(self):
            super().__init__()
            self._composition_call_count = 0

        def get(self, key, default=None):
            if key == "motifs":
                return {}
            if key == "composition":
                self._composition_call_count += 1
                return {"voices": [], "score_transforms": []} if self._composition_call_count == 1 else "bad"
            return super().get(key, default)

    with pytest.raises(ValueError):
        _extract_composition_sections(FlakyDocument())


def test_extract_composition_sections_rejects_invalid_voices_after_initial_validation():
    class FlakyComposition(dict):
        def __init__(self):
            super().__init__()
            self._voices_call_count = 0

        def get(self, key, default=None):
            if key == "voices":
                self._voices_call_count += 1
                return [] if self._voices_call_count == 1 else "not-a-list"
            if key == "score_transforms":
                return []
            return super().get(key, default)

    with pytest.raises(ValueError):
        _extract_composition_sections({"motifs": {}, "composition": FlakyComposition()})


def test_extract_composition_sections_rejects_invalid_score_transforms_after_initial_validation():
    class FlakyComposition(dict):
        def __init__(self):
            super().__init__()
            self._score_transforms_call_count = 0

        def get(self, key, default=None):
            if key == "voices":
                return []
            if key == "score_transforms":
                self._score_transforms_call_count += 1
                return [] if self._score_transforms_call_count == 1 else "not-a-list"
            return super().get(key, default)

    with pytest.raises(ValueError):
        _extract_composition_sections({"motifs": {}, "composition": FlakyComposition()})


def test_extract_phrase_transform_requests_rejects_non_list_voices_section():
    with pytest.raises(ValueError):
        _extract_phrase_transform_requests({})


def test_create_voice_plans_rejects_non_list_voices_section():
    with pytest.raises(ValueError):
        _create_voice_plans_from_document(
            voices_section={},
            plan_motifs={"seed": Motif(name="seed", tones=[Tone(440.0)])},
        )
