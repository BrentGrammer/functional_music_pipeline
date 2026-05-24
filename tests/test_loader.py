import json

import pytest

from composition.loader import load_composition_score
from score_model.score import Score


class TestLoadCompositionScore:
    def test_loads_valid_composition_returns_score(self, tmp_path):
        composition_file = tmp_path / "composition.json"
        composition_document = {
            "name": "Loader Study",
            "description": "Minimal persisted composition document.",
            "document_version": 1,
            "score": {
                "motifs": {
                    "seed": ["440:1.0"],
                },
                "voices": [
                    {
                        "phrases": [
                            {
                                "motifs": ["seed"],
                            }
                        ]
                    }
                ],
                "score_transforms": [],
            },
        }
        composition_file.write_text(json.dumps(composition_document), encoding="utf-8")

        score = load_composition_score(str(composition_file))

        assert isinstance(score, Score)
        assert len(score.voices) == 1
        assert len(score.voices[0].phrases) == 1
        assert score.voices[0].phrases[0].motifs[0].name == "seed"

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_composition_score("non_existent_file.json")

    def test_invalid_json_raises_error(self, tmp_path):
        invalid_json_file = tmp_path / "invalid.json"
        invalid_json_file.write_text("{'key': 'value',}")  # Malformed JSON

        with pytest.raises(json.JSONDecodeError):
            load_composition_score(str(invalid_json_file))
