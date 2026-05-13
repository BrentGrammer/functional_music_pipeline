import argparse
import logging
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import NoReturn

from audio_rendering.wav_writer import save_score_to_wav
from composition.loader import load_composition_score
from midi_rendering.midi_writer import save_score_to_midi

# Configure logging to output to stderr by default
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_NAME = "output"
OUTPUT_DIRECTORY = "output"
EXAMPLE_COMPOSITION_PATH = "compositions/geological_example.json"
OUTPUT_FORMAT_EXTENSIONS = {
    "wav": ".wav",
    "midi": ".mid",
}
DEFAULT_EXPORT_FORMAT = "wav"
MIDI_EXPORT_FORMAT = "midi"


def get_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Algorithmic Tone Transformer",
        add_help=False,  # Custom help message is handled in main()
    )
    parser.add_argument(
        "-c",
        "--composition-file",
        type=str,
        help="Path to the composition JSON file.",
        required=False,
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default=DEFAULT_OUTPUT_NAME,
        help=f"Output filename without extension (default: {DEFAULT_OUTPUT_NAME}).",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=list(OUTPUT_FORMAT_EXTENSIONS),
        default=DEFAULT_EXPORT_FORMAT,
        help=f"Output format to export (default: {DEFAULT_EXPORT_FORMAT}).",
    )
    parser.add_argument(
        "-h", "--help", action="help", default=argparse.SUPPRESS, help="Show this help message and exit."
    )
    return parser


def print_usage_and_exit(parser: argparse.ArgumentParser, exit_code: int = 0) -> NoReturn:
    print("Usage: python main.py --composition-file <path> --output-name <name> --output-format <wav|midi>")
    print(f"\nExample: python main.py --composition-file {EXAMPLE_COMPOSITION_PATH} --output-name my_composition")
    print(f"Example: python main.py --composition-file {EXAMPLE_COMPOSITION_PATH} --output-format midi --output-name my_composition")
    print("\nFor more options, run: python main.py --help")
    sys.exit(exit_code)


def _output_name_contains_directories(output_name: str) -> bool:
    posix_parts = PurePosixPath(output_name).parts
    windows_parts = PureWindowsPath(output_name).parts
    return not (len(posix_parts) == 1 and len(windows_parts) == 1 and output_name not in {".", ".."})


def build_output_filename(output_name: str, output_format: str) -> str:
    if not output_name.strip():
        raise ValueError("Output name cannot be empty.")
    if PurePosixPath(output_name).suffix or PureWindowsPath(output_name).suffix:
        raise ValueError("Output name should not include a file extension. Use --output-format to choose the file type.")
    if _output_name_contains_directories(output_name):
        raise ValueError("Output name should not include a directory. Use --output-name with a base filename only.")

    return f"{OUTPUT_DIRECTORY}/{output_name}{OUTPUT_FORMAT_EXTENSIONS[output_format]}"


def main(args: list[str] | None = None) -> None:
    parser = get_cli_parser()
    parsed_args = parser.parse_args(args if args is not None else sys.argv[1:])

    if not parsed_args.composition_file:
        logger.error("--composition-file is required.")
        print_usage_and_exit(parser, exit_code=1)
        return

    try:
        output_filename = build_output_filename(parsed_args.output_name, parsed_args.output_format)
        Path(OUTPUT_DIRECTORY).mkdir(parents=True, exist_ok=True)
        score = load_composition_score(parsed_args.composition_file)
        if parsed_args.output_format == MIDI_EXPORT_FORMAT:
            save_score_to_midi(score, filename=output_filename)
        else:
            save_score_to_wav(score, filename=output_filename)
        logger.info(f"Composition successfully rendered to '{output_filename}'")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
