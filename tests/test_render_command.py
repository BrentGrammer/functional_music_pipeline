import shutil
from pathlib import Path

import pytest

from cli.render_command import OUTPUT_DIRECTORY, print_usage_and_exit, render_composition

COMPOSITION_FILE = "compositions/composition_example.json"


def test_print_usage_and_exit_raises_with_exit_code_and_prints_usage(capsys):
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
def test_render_composition_creates_output_file(output_format: str, expected_suffix: str):
    output_basename = f"coverage_{output_format}"
    output_path = Path(OUTPUT_DIRECTORY) / f"{output_basename}{expected_suffix}"

    output_path.unlink(missing_ok=True)
    try:
        rendered_path = render_composition(COMPOSITION_FILE, output_basename, output_format)
        assert rendered_path.endswith(expected_suffix)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    finally:
        output_path.unlink(missing_ok=True)
        output_dir = Path(OUTPUT_DIRECTORY)
        if output_dir.exists() and not any(output_dir.iterdir()):
            shutil.rmtree(output_dir)
