import json

import pytest

from composition.loader import load_composition_score
from score_model.score import Score

COMPOSITION_FILE_PATH = "compositions/geological_example.json"


class TestLoadCompositionScore:
    def test_loads_valid_composition_returns_score(self):
        # Ensures the loader can parse a valid composition file and
        # return the expected Score domain object.
        score = load_composition_score(COMPOSITION_FILE_PATH)
        assert isinstance(score, Score)

    def test_missing_file_raises_file_not_found(self):
        # The loader must provide a clear error when the specified
        # composition file does not exist.
        with pytest.raises(FileNotFoundError, match="not found"):
            load_composition_score("non_existent_file.json")

    def test_invalid_json_raises_error(self, tmp_path):
        # If the file is not valid JSON, a clear error should be raised
        # during parsing.
        invalid_json_file = tmp_path / "invalid.json"
        invalid_json_file.write_text("{'key': 'value',}")  # Malformed JSON

        with pytest.raises(json.JSONDecodeError):
            load_composition_score(str(invalid_json_file))
