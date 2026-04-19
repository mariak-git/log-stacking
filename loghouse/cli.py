# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Command line interface for the log house stacking application.

Typical usage example:

  python -m loghouse --length 33 --logfile data/catalogue.csv --height 15.0
"""

import argparse
import logging
import sys

from loghouse.builder import BuildState, ScoringMethod, build_first_layer, \
  build_layer
from loghouse.catalogue import read_catalogue, get_wall_logs
from loghouse.config import (
  DEFAULT_STRUCT_L,
  DEFAULT_STRUCT_H,
  MIN_STRUCT_L,
  MIN_STRUCT_H_FT,
  FAT_END,
  THIN_END,
)
from loghouse.printer import get_writer, print_catalogue, print_layer, \
  print_summary

logger = logging.getLogger(__name__)


def _parse_args(argv=None) -> argparse.Namespace:
  """Parse command line arguments.

  Args:
    argv: Optional list of arguments for testing. Defaults to sys.argv.

  Returns:
    Parsed argument namespace.
  """
  parser = argparse.ArgumentParser(
    description="Log house stacking order generator.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
  )

  parser.add_argument(
    "--length",
    type=float,
    default=DEFAULT_STRUCT_L,
    metavar="FT",
    help="Structure side length in feet (square perimeter assumed).",
  )
  parser.add_argument(
    "--logfile",
    type=str,
    required=True,
    metavar="PATH",
    help="Path to the log catalogue CSV file.",
  )
  parser.add_argument(
    "--height",
    type=float,
    default=DEFAULT_STRUCT_H,
    metavar="FT",
    help="Target structure height in feet.",
  )
  parser.add_argument(
    "--level-margin",
    type=float,
    default=1.5,
    metavar="IN",
    help="Maximum allowed corner height difference in inches.",
  )
  parser.add_argument(
    "--taper-margin",
    type=float,
    default=0.01,
    metavar="IN/FT",
    help="Maximum taper difference for candidate selection in inches/ft.",
  )
  parser.add_argument(
    "--output",
    type=str,
    default=None,
    metavar="FILE",
    help="Output filename. Defaults to stdout.",
  )
  parser.add_argument(
    "--no-catalogue",
    action="store_true",
    default=False,
    help="Skip printing the log catalogue.",
  )
  parser.add_argument(
    "--verbose",
    action="store_true",
    default=False,
    help="Enable debug logging output.",
  )

  return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
  """Validate parsed arguments.

  Args:
    args: Parsed argument namespace.

  Raises:
    SystemExit: If any argument is invalid.
  """
  if args.length < MIN_STRUCT_L:
    print(
      f"Error: --length must be >= {MIN_STRUCT_L} ft, got {args.length}",
      file=sys.stderr
    )
    sys.exit(1)

  if args.height < MIN_STRUCT_H_FT:
    print(
      f"Error: --height must be >= {MIN_STRUCT_H_FT} ft, got {args.height}",
      file=sys.stderr
    )
    sys.exit(1)

  if args.level_margin <= 0:
    print(
      f"Error: --level-margin must be > 0, got {args.level_margin}",
      file=sys.stderr
    )
    sys.exit(1)

  if args.taper_margin <= 0:
    print(
      f"Error: --taper-margin must be > 0, got {args.taper_margin}",
      file=sys.stderr
    )
    sys.exit(1)


def _setup_logging(verbose: bool) -> None:
  """Configure logging level.

  Args:
    verbose: If True, enable DEBUG logging.
  """
  level = logging.DEBUG if verbose else logging.WARNING
  logging.basicConfig(
    level=level,
    format="%(levelname)s %(name)s: %(message)s",
  )


def main(argv=None) -> None:
  """Main entry point for the log stacking application.

  Args:
    argv: Optional list of arguments for testing.
  """
  args = _parse_args(argv)
  _setup_logging(args.verbose)
  _validate_args(args)

  # Convert height to inches for internal use
  target_height_in = args.height * 12.0

  # Load catalogue
  try:
    catalogue = read_catalogue(args.logfile)
  except FileNotFoundError:
    print(f"Error: catalogue file not found: {args.logfile}", file=sys.stderr)
    sys.exit(1)
  except ValueError as e:
    print(f"Error reading catalogue: {e}", file=sys.stderr)
    sys.exit(1)

  wall_logs = get_wall_logs(catalogue)
  if len(wall_logs) < 4:
    print(
      f"Error: not enough WALL logs in catalogue: {len(wall_logs)} < 4",
      file=sys.stderr
    )
    sys.exit(1)

  logger.debug("Loaded %d wall logs from catalogue", len(wall_logs))

  # Initialize build state
  state = BuildState(
    struct_l=args.length,
    target_height=target_height_in,
    level_margin=args.level_margin,
    taper_margin=args.taper_margin,
  )

  with get_writer(args.output) as writer:

    # Print catalogue if not disabled
    if not args.no_catalogue:
      print_catalogue(catalogue, list(wall_logs.keys()), writer)

    # Build first layer
    layer = build_first_layer(wall_logs, state)
    state.update_corner_heights(layer)
    state.layers.append(layer)
    print_layer(1, layer, state, writer)

    # Build remaining layers
    pass_end = THIN_END if layer.stack[0].pass_end == FAT_END else FAT_END
    layer_num = 2

    while not state.is_target_reached():
      if len(layer.indexes) < 4:
        logger.warning(
          "Not enough logs remaining to build layer #%d", layer_num
        )
        break

      # Alternate scoring: even layers use STD_DEV, odd use CONNECTION_DIST
      scoring = (
        ScoringMethod.STD_DEV
        if layer_num % 2 == 0
        else ScoringMethod.CONNECTION_DIST
      )

      try:
        layer = build_layer(
          logs=wall_logs,
          prev_layer=layer,
          pass_end=pass_end,
          state=state,
          scoring=scoring,
        )
      except ValueError as e:
        logger.warning("Could not build layer #%d: %s", layer_num, e)
        break

      state.update_corner_heights(layer)
      state.layers.append(layer)
      print_layer(layer_num, layer, state, writer)

      # Alternate pass end for next layer
      pass_end = THIN_END if pass_end == FAT_END else FAT_END
      layer_num += 1

    # Print summary
    print_summary(state, target_height_in, writer)
