import shutil
import json
from pathlib import Path

import pytest

from cli.render_command import OUTPUT_DIRECTORY, print_usage_and_exit, render_composition


def test_print_usage_and_exit_raises_with_exit_code_and_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        print_usage_and_exit(exit_code=2)
    # TODO: this should not test for specific strings, just that a string is returned
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "Usage: python main.py" in captured.out
    assert "--output-format <wav|midi>" in captured.out


@pytest.mark.parametrize(
    "output_format,expected_suffix",
    [("wav", ".wav"), ("midi", ".mid")],
)
def test_render_composition_creates_output_file(
    tmp_path: Path,
    output_format: str,
    expected_suffix: str,
) -> None:
    composition_file = tmp_path / "composition.json"
    composition_file.write_text(
        json.dumps(
            {
                "name": "Composition example",
                "description": "A short canon built from a single motif. The motif is presented plainly, then repeated later as a transposed answer and a reversed answer so the relationship stays easy to hear.",
                "score": {
                    "motifs": {
                        "subject": ["261.63:0.4", "293.66:0.4", "329.63:0.4", "392.00:0.6"]
                    },
                    "voices": [
                        {
                            "name": "SubjectVoice",
                            "phrases": [
                                {
                                    "comment": "Subject statement: the motif is heard in its plain form with no transforms.",
                                    "motifs": ["subject"],
                                }
                            ],
                        },
                        {
                            "name": "AnswerVoice",
                            "phrases": [
                                {
                                    "comment": "Answer entry: the same motif is transposed up a fifth and delayed with silence at the start so it enters later like a simple canon.",
                                    "motifs": ["subject"],
                                    "transforms": [
                                        {
                                            "name": "transpose",
                                            "params": {
                                                "semitones": 7.0,
                                            },
                                        },
                                        {
                                            "name": "pad_silence",
                                            "params": {
                                                "seconds": 2.2,
                                                "position": "start",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "name": "ReverseVoice",
                            "phrases": [
                                {
                                    "comment": "Reverse entry: the motif enters later again, but this time in reverse order so the imitation is easy to compare against the earlier voices.",
                                    "motifs": ["subject"],
                                    "transforms": [
                                        {
                                            "name": "reverse",
                                        },
                                        {
                                            "name": "pad_silence",
                                            "params": {
                                                "seconds": 4.6,
                                                "position": "start",
                                            },
                                        },
                                    ],
                                }
                            ],
                        },
                    ],
                    "score_transforms": [],
                },
            },
            indent=2,
        )
    )

    output_basename = f"coverage_{output_format}"
    output_path = Path(OUTPUT_DIRECTORY) / f"{output_basename}{expected_suffix}"

    output_path.unlink(missing_ok=True)
    try:
        rendered_path = render_composition(str(composition_file), output_basename, output_format)
        assert rendered_path.endswith(expected_suffix)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    finally:
        output_path.unlink(missing_ok=True)
        output_dir = Path(OUTPUT_DIRECTORY)
        if output_dir.exists() and not any(output_dir.iterdir()):
            shutil.rmtree(output_dir)
