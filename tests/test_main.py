from unittest.mock import patch

import pytest

from cli.render_command import build_output_filename, get_cli_parser
from main import main

# The contents are not read in these tests because load_composition_score is mocked.
VALID_COMPOSITION_FILE = "composition.json"


def test_cli_parser_accepts_output_name():
    args = get_cli_parser().parse_args(
        ["--composition-file", VALID_COMPOSITION_FILE, "--output-name", "composition"]
    )

    assert args.output_name == "composition"


@patch("main.render_composition")
def test_main_loads_composition_and_saves_wav(mock_render_composition):
    """
     Verifies the main function correctly orchestrates loading a composition
    and saving the resulting score when a valid composition file is provided.
    """
    mock_render_composition.return_value = "output/output.wav"
    args = ["--composition-file", VALID_COMPOSITION_FILE]
    main(args)

    mock_render_composition.assert_called_once_with(
        composition_file=VALID_COMPOSITION_FILE,
        output_name="output",
        output_format="wav",
    )


@patch("main.render_composition")
def test_main_output_name_overrides_default_filename_base(mock_render_composition):
    """
     Ensures the --output-name flag controls the filename base while the
    selected output format controls the extension.
    """
    mock_render_composition.return_value = "output/custom.wav"
    custom_output_name = "custom"
    args = ["--composition-file", VALID_COMPOSITION_FILE, "--output-name", custom_output_name]
    main(args)

    mock_render_composition.assert_called_once_with(
        composition_file=VALID_COMPOSITION_FILE,
        output_name=custom_output_name,
        output_format="wav",
    )


@patch("main.render_composition")
def test_main_routes_midi_export_to_midi_writer(mock_render_composition):
    midi_output_name = "composition"
    mock_render_composition.return_value = "output/composition.mid"
    args = ["--composition-file", VALID_COMPOSITION_FILE, "--output-format", "midi", "--output-name", midi_output_name]

    main(args)

    mock_render_composition.assert_called_once_with(
        composition_file=VALID_COMPOSITION_FILE,
        output_name=midi_output_name,
        output_format="midi",
    )


def test_build_output_filename_adds_extension_for_output_format():
    assert build_output_filename("composition", "midi") == "output/composition.mid"
    assert build_output_filename("composition", "wav") == "output/composition.wav"


def test_build_output_filename_rejects_output_name_with_extension():
    with pytest.raises(ValueError):
        build_output_filename("composition.mid", "midi")

    with pytest.raises(ValueError):
        build_output_filename("composition.txt", "wav")


def test_build_output_filename_rejects_empty_output_name():
    with pytest.raises(ValueError):
        build_output_filename("", "midi")

    with pytest.raises(ValueError):
        build_output_filename("   ", "wav")


def test_build_output_filename_rejects_output_name_with_directory():
    with pytest.raises(ValueError):
        build_output_filename("output/composition", "midi")


def test_build_output_filename_rejects_windows_style_path():
    with pytest.raises(ValueError):
        build_output_filename(r"output\\composition", "midi")


@patch("main.print_usage_and_exit")
@patch("main.logger")
def test_main_missing_composition_file_arg_exits_with_error(mock_logger, mock_print_usage_and_exit):
    """
     The program must exit gracefully with a clear error and usage
    instructions if the required --composition-file argument is omitted.
    """
    main([])
    mock_logger.error.assert_called_with("--composition-file is required.")
    mock_print_usage_and_exit.assert_called_once_with(exit_code=1)


@patch("sys.exit")
@patch("main.logger")
@patch("main.render_composition", side_effect=FileNotFoundError("File not found"))
def test_main_non_existent_composition_file_exits_with_error(mock_render_composition, mock_logger, mock_exit):
    """
     If the user provides a path to a file that does not exist, the
    program should report the error clearly and exit, preventing a crash.
    """
    args = ["--composition-file", "non_existent.json"]
    main(args)

    mock_render_composition.assert_called_once_with(
        composition_file="non_existent.json",
        output_name="output",
        output_format="wav",
    )
    mock_logger.error.assert_called_with("File not found")
    mock_exit.assert_called_once_with(1)

def test_main_invalid_output_name_exits_with_generic_error(caplog):
    caplog.set_level("ERROR")

    with pytest.raises(SystemExit) as exc_info:
        main(["--composition-file", VALID_COMPOSITION_FILE, "--output-name", "bad.mid"])

    assert exc_info.value.code == 1
