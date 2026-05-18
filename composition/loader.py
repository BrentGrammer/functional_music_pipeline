import json
import os

from composition.parser import generate_score_plan
from composition.transformer import transform_score
from score_model.score import Score


def load_composition_score(composition_filepath: str) -> Score:
    """
    Loads a composition from a JSON file, parses it, and returns a Score object.

    Args:
        composition_filepath: The path to the composition JSON file.

    Returns:
        A Score object representing the parsed composition.

    Raises:
        FileNotFoundError: If the composition file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    if not os.path.exists(composition_filepath):
        raise FileNotFoundError(f"Composition file '{composition_filepath}' not found.")

    with open(composition_filepath, "r", encoding="utf-8") as composition_file:
        json_data = json.load(composition_file)

    return transform_score(generate_score_plan(json_data))
