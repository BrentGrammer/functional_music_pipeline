from unittest.mock import ANY, patch

import pytest

from main import build_output_filename, get_cli_parser, main

# The contents are not read in these tests because load_composition_score is mocked.
VALID_COMPOSITION_FILE = "composition.json"


def test_cli_parser_accepts_output_name():
    args = get_cli_parser().parse_args(
        ["--composition-file", VALID_COMPOSITION_FILE, "--output-name", "composition"]
    )

    assert args.output_name == "composition"


@patch("main.save_score_to_wav")
@patch("main.Path.mkdir")
@patch("main.load_composition_score")
def test_main_loads_composition_and_saves_wav(mock_load_score, mock_mkdir, mock_save_wav):
    """
     Verifies the main function correctly orchestrates loading a composition
    and saving the resulting score when a valid composition file is provided.
    """
    args = ["--composition-file", VALID_COMPOSITION_FILE]
    main(args)

    mock_load_score.assert_called_once_with(VALID_COMPOSITION_FILE)
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_save_wav.assert_called_once_with(ANY, filename="output/output.wav")


@patch("main.save_score_to_wav")
@patch("main.Path.mkdir")
@patch("main.load_composition_score")
def test_main_output_name_overrides_default_filename_base(mock_load_score, mock_mkdir, mock_save_wav):
    """
     Ensures the --output-name flag controls the filename base while the
    selected output format controls the extension.
    """
    custom_output_name = "custom"
    args = ["--composition-file", VALID_COMPOSITION_FILE, "--output-name", custom_output_name]
    main(args)

    mock_load_score.assert_called_once_with(VALID_COMPOSITION_FILE)
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_save_wav.assert_called_once_with(ANY, filename="output/custom.wav")


@patch("main.save_score_to_midi")
@patch("main.save_score_to_wav")
@patch("main.Path.mkdir")
@patch("main.load_composition_score")
def test_main_routes_midi_export_to_midi_writer(mock_load_score, mock_mkdir, mock_save_wav, mock_save_midi):
    midi_output_name = "composition"
    args = ["--composition-file", VALID_COMPOSITION_FILE, "--output-format", "midi", "--output-name", midi_output_name]

    main(args)

    mock_load_score.assert_called_once_with(VALID_COMPOSITION_FILE)
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_save_midi.assert_called_once_with(ANY, filename="output/composition.mid")
    mock_save_wav.assert_not_called()


def test_build_output_filename_adds_extension_for_output_format():
    assert build_output_filename("composition", "midi") == "output/composition.mid"
    assert build_output_filename("composition", "wav") == "output/composition.wav"


def test_build_output_filename_rejects_output_name_with_extension():
    with pytest.raises(ValueError, match="Output name should not include a file extension."):
        build_output_filename("composition.mid", "midi")

    with pytest.raises(ValueError, match="Output name should not include a file extension."):
        build_output_filename("composition.txt", "wav")


def test_build_output_filename_rejects_empty_output_name():
    with pytest.raises(ValueError, match="Output name cannot be empty."):
        build_output_filename("", "midi")

    with pytest.raises(ValueError, match="Output name cannot be empty."):
        build_output_filename("   ", "wav")


def test_build_output_filename_rejects_output_name_with_directory():
    with pytest.raises(ValueError, match="Output name should not include a directory."):
        build_output_filename("output/composition", "midi")


def test_build_output_filename_rejects_windows_style_path():
    with pytest.raises(ValueError, match="Output name should not include a directory."):
        build_output_filename(r"output\\composition", "midi")


@patch("sys.exit")
@patch("main.logger")
def test_main_missing_composition_file_arg_exits_with_error(mock_logger, mock_exit):
    """
     The program must exit gracefully with a clear error and usage
    instructions if the required --composition-file argument is omitted.
    """
    main([])
    mock_logger.error.assert_called_with("--composition-file is required.")
    mock_exit.assert_called_once_with(1)


@patch("sys.exit")
@patch("main.logger")
@patch("main.load_composition_score", side_effect=FileNotFoundError("File not found"))
def test_main_non_existent_composition_file_exits_with_error(
    mock_load_score, mock_logger, mock_exit
):
    """
     If the user provides a path to a file that does not exist, the
    program should report the error clearly and exit, preventing a crash.
    """
    args = ["--composition-file", "non_existent.json"]
    main(args)

    mock_load_score.assert_called_once_with("non_existent.json")
    mock_logger.error.assert_called_with("File not found")
    mock_exit.assert_called_once_with(1)
