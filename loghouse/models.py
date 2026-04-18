# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Core domain models for the log house stacking algorithm.

Contains two main classes:
    LogEntry: A raw catalogue entry representing an unplaced log.
    Log: A placed log with computed dimensions based on wall orientation.
    Layer: A course of 4 logs forming one level of the wall.
"""

import logging
from dataclasses import dataclass
from loghouse.config import (THIN_END, FAT_END, PASS_END_LABELS, CORNERS,
                             ORIENT, SW, NW, NE, SE, NORTH, WEST, EAST, SOUTH)

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
  """A raw log entry from the catalogue.

  Attributes:
      index: Unique identifier from the catalogue.
      d_top: Diameter at the narrow (top) end in inches.
      d_butt: Diameter at the wide (butt) end in inches.
      length: Length of the log in feet.
  """
  index: int
  d_top: float
  d_butt: float
  length: float

  def __post_init__(self) -> None:
    """Validate log dimensions on construction."""
    if self.length <= 0:
      raise ValueError(
          f"Log #{self.index}: length must be positive, got {self.length}")
    if self.d_top < 0 or self.d_butt < 0:
      raise ValueError(f"Log #{self.index}: diameters must be non-negative")
    if self.d_butt < self.d_top:
      raise ValueError(f"Log #{self.index}: d_butt must be >= d_top")

  @property
  def taper(self) -> float:
    """Taper rate in inches per foot."""
    return (self.d_butt - self.d_top) / self.length


class Log:
  """A placed log with computed dimensions based on wall orientation.

  A Log is created from a LogEntry when it is assigned to a specific
  wall in a layer. The overdangle and adjusted end diameters are
  computed at construction time.

  Attributes:
      entry: The original LogEntry from the catalogue.
      index: Unique identifier, copied from entry for convenience.
      pass_end: Which end (THIN_END or FAT_END) is the pass end.
      pass_str: Human readable pass end label.
      struct_l: The wall length this log is placed against.
      overdangle: How much the log extends past struct_l.
      top_new: Adjusted top diameter after overdangle calculation.
      butt_new: Adjusted butt diameter after overdangle calculation.
  """

  def __init__(self, entry: LogEntry, pass_end: int, struct_l: float) -> None:
    """Place a log on a wall.

    Args:
        entry: The catalogue entry for this log.
        pass_end: THIN_END or FAT_END indicating orientation.
        struct_l: The wall length in feet.

    Raises:
        ValueError: If log is shorter than struct_l.
    """
    if entry.length < struct_l:
      raise ValueError(
          f"Log #{entry.index} length {entry.length:.2f} is shorter "
          f"than struct_l {struct_l:.2f}"
      )

    self.entry = entry
    self.index = entry.index
    self.pass_end = pass_end
    self.struct_l = struct_l

    self.overdangle = entry.length - struct_l
    self.top_new = entry.d_top
    self.butt_new = entry.d_butt

    self._compute_adjusted_ends()

  @property
  def pass_str(self) -> str:
    """Human readable pass end label."""
    return PASS_END_LABELS[self.pass_end]

  def _compute_adjusted_ends(self) -> None:
    """Adjust end diameters based on overdangle and pass end."""
    if self.pass_end == FAT_END:
      # Butt end is the pass end — trim butt diameter by overdangle
      self.butt_new = self.entry.d_butt - self.overdangle * self.entry.taper
    else:
      # Thin end is the pass end — adjust top diameter upward
      self.top_new = self.entry.d_top + self.overdangle * self.entry.taper

  def get_corner_diameter(self) -> float:
    """Get the diameter at the corner connection point.

    Returns the adjusted diameter at the pass end — the diameter
    of this log at exactly struct_l from its start.

    Returns:
        The adjusted diameter at the corner.
    """
    return self.butt_new if self.pass_end == FAT_END else self.top_new

  def __repr__(self) -> str:
    return (
        f"Log(index={self.index}, pass={self.pass_str}, "
        f"top={self.entry.d_top:.2f}, butt={self.entry.d_butt:.2f}, "
        f"top_new={self.top_new:.2f}, butt_new={self.butt_new:.2f}, "
        f"overdangle={self.overdangle:.2f})"
    )


class Layer:
  """A single course of 4 logs forming one level of the wall.

  Logs are arranged counter-clockwise when viewed from above:
      SW(0) → NW(1) → NE(2) → SE(3) → back to SW

  Attributes:
      stack: List of 4 placed Log objects for this layer.
      indexes: Remaining catalogue indices after this layer is built.
      corners: Corner height contributions keyed by corner constant.
      tapers: Wall taper rates keyed by cardinal direction constant.
      struct_l: Wall length, carried from the logs.
  """

  def __init__(self, indexes: list[int], stack: list[Log]) -> None:
    """Initialize a layer and compute corner heights and wall tapers.

    Args:
        indexes: Remaining log indices after selecting this layer's logs.
        stack: List of exactly 4 placed Log objects.

    Raises:
        ValueError: If stack does not contain exactly 4 logs.
    """
    if len(stack) != 4:
      raise ValueError(f"Layer requires exactly 4 logs, got {len(stack)}")

    self.stack = list(stack)
    self.indexes = list(indexes)
    self.struct_l = stack[0].struct_l
    self.corners: dict[int, float] = {}
    self.tapers: dict[int, float] = {}

    self._init_corners()
    self._init_tapers()

  def _init_corners(self) -> None:
    """Compute corner height contribution for each corner.

    At each corner two logs meet counter-clockwise:
    - log1: the log whose pass end (butt) sits AT this corner
    - log2: the adjacent log whose overdangle end crosses OVER log1

    The corner height is max(log1.corner_diameter, log2.overdangle_diameter).
    log1.pass_end determines which end of log2 is presenting at this corner
    since they always alternate together.
    """
    for corner in CORNERS:
      log1 = self.stack[corner]
      # Counter-clockwise: previous log in the cycle
      connection = (corner + len(CORNERS) - 1) % len(CORNERS)
      log2 = self.stack[connection]

      c1 = log1.get_corner_diameter()

      # log1.pass_end tells us which end of log2 is at this corner
      if log1.pass_end == THIN_END:
        c2 = log2.top_new
      else:
        c2 = log2.butt_new

      self.corners[corner] = max(c1, c2)
      logger.debug("Corner %s height = %.2f",
                   CORNERS[corner], self.corners[corner])

  def _init_tapers(self) -> None:
    """Compute taper rate for each wall from corner height differences."""
    self.tapers[NORTH] = abs(
        self.corners[SW] - self.corners[NW]) / self.struct_l
    self.tapers[EAST] = abs(
        self.corners[NW] - self.corners[NE]) / self.struct_l
    self.tapers[SOUTH] = abs(
        self.corners[NE] - self.corners[SE]) / self.struct_l
    self.tapers[WEST] = abs(
        self.corners[SE] - self.corners[SW]) / self.struct_l
    logger.debug("Wall tapers: %s", {
                 ORIENT[k]: f"{v:.3f}" for k, v in self.tapers.items()})

  def validate_indexes(self) -> None:
    """Verify no layer log appears in the remaining indexes.

    Raises:
        ValueError: If a log in the stack is also in indexes.
    """
    for log in self.stack:
      if log.index in self.indexes:
        raise ValueError(
            f"Log #{log.index} is in both the stack and remaining indexes"
        )

  def __repr__(self) -> str:
    log_ids = [log.index for log in self.stack]
    return (f"Layer(logs={log_ids}, "
            f"remaining={len(self.indexes)}, "
            f"corners={self.corners})")
