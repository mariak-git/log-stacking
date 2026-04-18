# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Log selection functions for the log house stacking algorithm.

This module contains functions for selecting logs from the catalogue
to form layers, based on diameter matching and taper similarity.
"""

import logging
from typing import Optional

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