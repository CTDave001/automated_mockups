"""
Command-line interface for the mockup generator.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .calculator import MockupCalculator
from .generator import MockupGenerator, Alignment, ScaleMode
from .utils import Color, setup_logging


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="mockup-generator",
        description="Automated product mockup generator - Create mockups at scale.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calculate box positions from templates
  mockup-generator calculate --hex-color "#FF0000" --input templates/ --output params.json

  # Generate mockups
  mockup-generator generate --params params.json --designs designs/ --mockups templates/ --output output/

  # Full pipeline
  mockup-generator calculate --color 255 0 0 --input templates/ --output params.json
  mockup-generator generate --params params.json --designs designs/ --mockups templates/ --output output/
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress all output except errors"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Calculate command
    calc_parser = subparsers.add_parser(
        "calculate",
        help="Calculate box positions from mockup templates"
    )

    color_group = calc_parser.add_mutually_exclusive_group(required=True)
    color_group.add_argument(
        "--color",
        type=int,
        nargs=3,
        metavar=("R", "G", "B"),
        help="Target color as RGB values (0-255)"
    )
    color_group.add_argument(
        "--hex-color",
        type=str,
        metavar="HEX",
        help="Target color as hex string (e.g., '#FF0000' or 'FF0000')"
    )

    calc_parser.add_argument(
        "-i", "--input",
        type=str,
        required=True,
        help="Input directory containing mockup templates"
    )

    calc_parser.add_argument(
        "-o", "--output",
        type=str,
        default="parameters.json",
        help="Output JSON file for parameters (default: parameters.json)"
    )

    calc_parser.add_argument(
        "--tolerance",
        type=int,
        default=30,
        help="Color matching tolerance (default: 30)"
    )

    calc_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process subdirectories recursively"
    )

    # Generate command
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate mockups from designs and templates"
    )

    gen_parser.add_argument(
        "-p", "--params",
        type=str,
        required=True,
        help="Path to parameters JSON file"
    )

    gen_parser.add_argument(
        "-d", "--designs",
        type=str,
        required=True,
        help="Directory containing design images"
    )

    gen_parser.add_argument(
        "-m", "--mockups",
        type=str,
        required=True,
        help="Directory containing mockup templates"
    )

    gen_parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output directory for generated mockups"
    )

    gen_parser.add_argument(
        "--alignment",
        type=str,
        choices=[a.value for a in Alignment],
        default="top_center",
        help="Design alignment within placeholder (default: top_center)"
    )

    gen_parser.add_argument(
        "--scale-mode",
        type=str,
        choices=[s.value for s in ScaleMode],
        default="fit",
        help="How to scale designs (default: fit)"
    )

    gen_parser.add_argument(
        "--format",
        type=str,
        choices=["PNG", "JPEG", "WEBP"],
        default="PNG",
        help="Output image format (default: PNG)"
    )

    gen_parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="Output quality for JPEG (1-100, default: 95)"
    )

    gen_parser.add_argument(
        "--pattern",
        type=str,
        default="{design}_{mockup}",
        help="Output filename pattern (default: {design}_{mockup})"
    )

    gen_parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing"
    )

    gen_parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )

    return parser


def cmd_calculate(args) -> int:
    """Execute the calculate command."""
    # Parse color
    if args.color:
        color = Color(*args.color)
    else:
        color = Color.from_hex(args.hex_color)

    print(f"Target color: {color}")
    print(f"Input directory: {args.input}")
    print(f"Output file: {args.output}")
    print()

    # Create calculator and process
    calculator = MockupCalculator(
        target_color=color,
        color_tolerance=args.tolerance
    )

    try:
        parameters = calculator.process_directory(
            args.input,
            recursive=args.recursive
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not parameters:
        print("Warning: No boxes detected in any images.", file=sys.stderr)
        return 1

    # Save parameters
    calculator.save_parameters(parameters, args.output)
    print(f"Saved parameters for {len(parameters)} mockups to {args.output}")

    return 0


def cmd_generate(args) -> int:
    """Execute the generate command."""
    print(f"Parameters file: {args.params}")
    print(f"Designs directory: {args.designs}")
    print(f"Mockups directory: {args.mockups}")
    print(f"Output directory: {args.output}")
    print()

    # Load parameters
    try:
        parameters = MockupCalculator.load_parameters(args.params)
    except FileNotFoundError:
        print(f"Error: Parameters file not found: {args.params}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading parameters: {e}", file=sys.stderr)
        return 1

    # Create generator
    generator = MockupGenerator(
        parameters=parameters,
        alignment=Alignment(args.alignment),
        scale_mode=ScaleMode(args.scale_mode),
        output_quality=args.quality,
        output_format=args.format
    )

    # Progress callback
    def progress(completed: int, total: int):
        pct = (completed / total) * 100
        print(f"\rProgress: {completed}/{total} ({pct:.1f}%)", end="", flush=True)

    # Generate mockups
    try:
        results = generator.generate_all(
            design_dir=args.designs,
            mockup_dir=args.mockups,
            output_dir=args.output,
            naming_pattern=args.pattern,
            parallel=not args.no_parallel,
            max_workers=args.workers,
            progress_callback=progress
        )
    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    print()  # Newline after progress

    # Summary
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    print(f"\nGeneration complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if failed > 0:
        print("\nFailed generations:")
        for r in results:
            if not r.success:
                print(f"  - {r.design_name} + {r.mockup_name}: {r.error}")

    return 0 if failed == 0 else 1


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING

    setup_logging(level=log_level)

    # Execute command
    if args.command == "calculate":
        return cmd_calculate(args)
    elif args.command == "generate":
        return cmd_generate(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
