# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Output and display functions for the log house stacking algorithm.

Handles printing to stdout and optionally to a file.

Typical usage example:

  with get_writer(filename) as writer:
    print_catalogue(catalogue, indexes, writer)
    print_layer(1, layer, state, writer)
    print_summary(state, target_height, writer)
"""

import sys
from contextlib import contextmanager
from typing import IO, Optional

from loghouse.builder import BuildState
from loghouse.config import CORNERS, SW, NW, NE, SE
from loghouse.models import Layer

# Notes keywords that trigger printing
_NOTES_KEYWORDS = {"straight", "bowed", "crooked"}

# Line width
_LINE_WIDTH = 60


def _line(writer: IO) -> None:
  """Print a separator line."""
  writer.write("-" * _LINE_WIDTH + "\n")


def _feet_and_inches(inches: float) -> str:
  """Convert inches to a formatted feet and inches string.

  Args:
    inches: Value in inches.

  Returns:
    String in format 'X ft Y in'.
  """
  feet = int(inches // 12)
  remaining = inches % 12
  return f"{feet} ft {remaining:.1f} in"


def _format_notes(notes: str) -> str:
  """Return notes string if it contains a relevant keyword.

  Args:
    notes: Raw notes string from catalogue entry.

  Returns:
    Formatted notes string or empty string.
  """
  if any(kw in notes.lower() for kw in _NOTES_KEYWORDS):
    return f"  [{notes}]"
  return ""


@contextmanager
def get_writer(filename: Optional[str] = None):
  """Context manager returning a writer for stdout or a file.

  Args:
    filename: Optional output filename. If None, writes to stdout.

  Yields:
    A file-like writer object.
  """
  if filename:
    with open(filename, "w", encoding="utf-8") as f:
      yield f
  else:
    yield sys.stdout


def print_catalogue(
  catalogue: dict,
  indexes: list[int],
  writer: IO = sys.stdout,
) -> None:
  """Print the wall log catalogue sorted by thin end diameter.

  Args:
    catalogue: Dict of CatalogueEntry objects keyed by index.
    indexes: List of log indexes to print.
    writer: Output writer (stdout or file).
  """
  _line(writer)
  header = "WALL LOGS CATALOGUE (SORTED BY THIN ENDS)"
  writer.write(f"|{header.center(_LINE_WIDTH - 2)}|\n")
  _line(writer)
  writer.write(
    f"|{'Num'.ljust(10)}"
    f"{'Top (in)'.ljust(12)}"
    f"{'Butt (in)'.ljust(12)}"
    f"{'Length (ft)'.ljust(12)}"
    f"{'Taper (in)'.ljust(10)}|\n"
  )
  _line(writer)

  sorted_indexes = sorted(indexes, key=lambda i: catalogue[i].entry.d_top)
  for i in sorted_indexes:
    ce = catalogue[i]
    entry = ce.entry
    notes = _format_notes(ce.notes)
    writer.write(
      f"|  LOG# {str(i).ljust(5)}"
      f"{entry.d_top:>10.2f}  "
      f"{entry.d_butt:>10.2f}  "
      f"{entry.length:>10.2f}  "
      f"{entry.taper:>8.3f}  "
      f"{notes}|\n"
    )
    _line(writer)
  writer.write("\n")


def print_layer(
  layer_num: int,
  layer: Layer,
  state: BuildState,
  writer: IO = sys.stdout,
) -> None:
  """Print a single layer with corner info and cumulative heights.

  Args:
    layer_num: Layer number (1-based).
    layer: The layer to print.
    state: Current build state with cumulative corner heights.
    writer: Output writer (stdout or file).
  """
  _line(writer)
  writer.write(f"\nLAYER #{layer_num}\n")
  _line(writer)

  corner_labels = {SW: "SW", NW: "NW", NE: "NE", SE: "SE"}
  for corner in CORNERS:
    log = layer.stack[corner]
    writer.write(
      f"{corner_labels[corner]}: "
      f"LOG# {log.index:<5} "
      f"{log.pass_str:<10} "
      f"overdangle={log.overdangle:.2f}  "
      f"corner={layer.corners[corner]:.2f}\n"
    )

  writer.write("\nCorner heights:\n")
  writer.write(
    "  " + "  ".join(
      f"{corner_labels[c]}: {layer.corners[c]:.2f}"
      for c in CORNERS
    ) + "\n"
  )

  writer.write("\nCumulative heights:\n")
  writer.write(
    "  " + "  ".join(
      f"{corner_labels[c]}: {state.corner_heights[c]:.2f}"
      for c in CORNERS
    ) + "\n"
  )

  writer.write(f"\nLogs remaining: {len(layer.indexes)}\n")


def print_summary(
  state: BuildState,
  target_height: float,
  writer: IO = sys.stdout,
) -> None:
  """Print the final stacking summary.

  Args:
    state: Final build state.
    target_height: Target structure height in inches.
    writer: Output writer (stdout or file).
  """
  actual_height = max(state.corner_heights.values())
  height_margin = abs(actual_height - target_height)
  std_dev = state.corner_std_dev()

  # Determine status
  statuses = []
  if height_margin > 6.0:
    if actual_height > target_height:
      statuses.append("WARNING: height exceeded")
    else:
      statuses.append("WARNING: not enough logs")
  if not state.is_level():
    statuses.append("WARNING: not level")
  status = " | ".join(statuses) if statuses else "OK"

  _line(writer)
  writer.write("SUMMARY\n")
  _line(writer)
  writer.write(f"{'Total layers:':<20} {len(state.layers)}\n")
  writer.write(f"{'Target height:':<20} {_feet_and_inches(target_height)}\n")
  writer.write(
    f"{'Actual height:':<20} {_feet_and_inches(actual_height)} "
    f"(max of 4 corners)\n"
  )
  writer.write(f"{'Height margin:':<20} {height_margin:.1f} in\n")
  writer.write(f"{'Level (std dev):':<20} {std_dev:.2f} in\n")
  writer.write(f"{'Status:':<20} {status}\n")
  _line(writer)
