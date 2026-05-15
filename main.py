import logging
import sys

from cli.render_command import get_cli_parser, print_usage_and_exit, render_composition

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main(args: list[str] | None = None) -> None:
    parser = get_cli_parser()
    parsed_args = parser.parse_args(args if args is not None else sys.argv[1:])

    if not parsed_args.composition_file:
        logger.error("--composition-file is required.")
        print_usage_and_exit(exit_code=1)
        return

    try:
        output_filename = render_composition(
            composition_file=parsed_args.composition_file,
            output_name=parsed_args.output_name,
            output_format=parsed_args.output_format,
        )
        logger.info(f"Composition successfully rendered to '{output_filename}'")
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
