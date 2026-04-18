# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Log selection functions for the log house stacking algorithm.

This module contains functions for selecting logs from the catalogue
to form layers, based on diameter matching and taper similarity.
"""

import logging
#from typing import Optional

from loghouse.config import FAT_END, THIN_END
from loghouse.models import Log, LogEntry

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
