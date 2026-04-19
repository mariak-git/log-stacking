# Copyright 2015-2026 Maria Mercury <mariak>. All Rights Reserved.

"""Log selection functions for the log house stacking algorithm.

This module contains functions for selecting logs from the catalogue
to form layers, based on diameter matching and taper similarity.
"""

import logging

from loghouse.config import FAT_END, THIN_END, ORIENT
from loghouse.models import Log, LogEntry
from loghouse.utils import avg_diameter

logger = logging.getLogger(__name__)


def pick_first(
  logs: dict[int, LogEntry],
  index: int,
  pass_end: int,
  struct_l: float,
) -> Log:
  """Select the first log in a layer by index and orientation.

  Args:
    logs: Dict of available LogEntry objects keyed by index.
    index: Index of the log to select.
    pass_end: THIN_END or FAT_END indicating orientation.
    struct_l: Wall length in feet.

  Returns:
    A placed Log object.

  Raises:
    KeyError: If index is not found in logs.
  """
  entry = logs[index]
  log = Log(entry=entry, pass_end=pass_end, struct_l=struct_l)
  logger.debug(
    "pick_first: log #%d (%s END) corner_d=%.2f",
    log.index, log.pass_str, log.get_corner_diameter()
  )
  return log

def pick_next(
  log: Log,
  logs: dict[int, LogEntry],
  indexes: list[int],
  struct_l: float,
) -> Log:
  """Select the next log in a layer by finding the closest diameter match.

  Finds the log from remaining indexes whose relevant end diameter
  is closest to the current log's corner diameter. The next log's
  pass end is always opposite to the current log's pass end.
  FAT connects to FAT, THIN connects to THIN.

  Args:
    log: The last placed Log in the current layer.
    logs: Dict of all available LogEntry objects keyed by index.
    indexes: List of remaining available log indexes.
    struct_l: Wall length in feet.

  Returns:
    The best matching placed Log object.

  Raises:
    ValueError: If indexes list is empty.
  """
  if not indexes:
    raise ValueError("No remaining logs to select from")

  d_corner = log.get_corner_diameter()
  logger.debug(
    "pick_next: matching against log #%d (%s END) corner_d=%.2f",
    log.index, log.pass_str, d_corner
  )

  def diameter_distance(i: int) -> float:
    """Distance between corner diameter and candidate log's matching end."""
    entry = logs[i]
    d = entry.d_butt if log.pass_end == FAT_END else entry.d_top
    return abs(d_corner - d)

  i_min = min(indexes, key=diameter_distance)

  logger.debug(
    "pick_next: best match is log #%d with distance=%.2f",
    i_min, diameter_distance(i_min)
  )

  next_pass_end = THIN_END if log.pass_end == FAT_END else FAT_END
  return Log(entry=logs[i_min], pass_end=next_pass_end, struct_l=struct_l)


def pick_layer_candidates(
  logs: dict[int, LogEntry],
  layer: "Layer",
  taper_margin: float = 0.01,
) -> list[int]:
  """Find candidate logs for the next layer based on taper similarity.

  Filters remaining logs to those whose taper is within taper_margin
  of any wall taper in the previous layer. If fewer than 4 candidates
  are found, falls back to logs with largest average diameter and
  closest taper to the previous layer's wall tapers.

  Args:
    logs: Dict of all available LogEntry objects keyed by index.
    layer: The previous layer to match tapers against.
    taper_margin: Maximum taper difference to consider a match,
      in inches per foot. Defaults to 0.01. A larger margin may
      be needed towards the end of log selection when fewer logs
      are available. Controlled via CLI --taper-margin parameter.

  Returns:
    List of log indexes that are candidates for the next layer.
    Always contains at least 4 indexes if enough logs remain.

  Raises:
    ValueError: If fewer than 4 logs remain in layer.indexes.
  """
  if len(layer.indexes) < 4:
    raise ValueError(
      f"Not enough logs remaining: {len(layer.indexes)} < 4"
    )

  def min_taper_dist(i: int) -> float:
    """Minimum taper distance to any wall in previous layer."""
    return min(
      abs(logs[i].taper - layer.tapers[wall])
      for wall in ORIENT
    )

  # --- Main candidate selection: match by taper ---
  candidates = set(
    i for i in layer.indexes
    if min_taper_dist(i) <= taper_margin
  )

  logger.debug(
    "pick_layer_candidates: found %d candidates within taper margin %.3f",
    len(candidates), taper_margin
  )

  # --- Fallback: not enough candidates found ---
  if len(candidates) < 4:
    logger.debug(
      "pick_layer_candidates: falling back to sorted selection"
    )
    remaining = sorted(
      (i for i in layer.indexes if i not in candidates),
      key=lambda i: (-avg_diameter(logs[i]), min_taper_dist(i))
    )
    for i in remaining:
      if len(candidates) >= 4:
        break
      candidates.add(i)
      logger.debug("pick_layer_candidates: fallback added log #%d", i)

  return list(candidates)
