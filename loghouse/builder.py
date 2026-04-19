# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Layer building functions for the log house stacking algorithm.

Builds layers of logs using a greedy algorithm with exhaustive
combination search for optimal corner leveling.

# TODO(mariak): Implement lookahead algorithm as an alternative
# to the greedy approach for better global optimization.
"""

import logging
import math
from dataclasses import dataclass, field

from loghouse.config import (
  FAT_END,
  THIN_END,
  CORNERS,
  SW, NW, NE, SE,
)
from loghouse.models import LogEntry, Layer
from loghouse.selector import pick_first, pick_next

logger = logging.getLogger(__name__)

# Default target height: 10 courses at 18 inches each, converted to feet
_DEFAULT_TARGET_HEIGHT_FT = (18 * 10) / 12


@dataclass
class BuildState:
  """Accumulated state of the log stacking process.

  Attributes:
    layers: List of stacked layers in order.
    corner_heights: Cumulative corner heights in inches at SW/NW/NE/SE.
    struct_l: Wall length in feet.
    target_height: Target structure height in inches from CLI.
    level_margin: Max allowed corner height difference in inches.
    taper_margin: Max taper difference for candidate selection in inches/ft.
  """
  struct_l: float
  target_height: float = _DEFAULT_TARGET_HEIGHT_FT * 12
  level_margin: float = 1.5
  taper_margin: float = 0.01
  layers: list = field(default_factory=list)
  corner_heights: dict = field(default_factory=lambda: {
    SW: 0.0, NW: 0.0, NE: 0.0, SE: 0.0
  })

  def update_corner_heights(self, layer: Layer) -> None:
    """Add the latest layer's corner contributions to running totals.

    Args:
      layer: The newly built layer to add.
    """
    for corner in CORNERS:
      self.corner_heights[corner] += layer.corners[corner]

  def is_level(self) -> bool:
    """Check if cumulative corner heights are within level_margin.

    Returns:
      True if max corner height difference <= level_margin.
    """
    heights = list(self.corner_heights.values())
    return (max(heights) - min(heights)) <= self.level_margin

  def is_target_reached(self) -> bool:
    """Check if target height has been reached.

    Returns:
      True if max cumulative corner height >= target_height.
    """
    return max(self.corner_heights.values()) >= self.target_height

  def corner_std_dev(self) -> float:
    """Calculate standard deviation of cumulative corner heights.

    Returns:
      Standard deviation of the 4 corner heights.
    """
    heights = list(self.corner_heights.values())
    mean = sum(heights) / len(heights)
    variance = sum((h - mean) ** 2 for h in heights) / len(heights)
    return math.sqrt(variance)

  def __repr__(self) -> str:
    return (
      f"BuildState(layers={len(self.layers)}, "
      f"corners={self.corner_heights}, "
      f"level={self.is_level()}, "
      f"target_reached={self.is_target_reached()})"
    )

# TODO(mariak): Cap candidate set to improve performance with large catalogues.
# TODO(mariak): Add early termination when std_dev == 0.0.
# TODO(mariak): Consider caching pick_next results across combinations.
def try_layer(
  logs: dict[int, LogEntry],
  indexes: list[int],
  index: int,
  pass_end: int,
  struct_l: float,
) -> Layer:
  """Build one layer starting from a specific log using greedy selection.

  Selects 4 logs greedily: picks the first log by index and pass_end,
  then uses pick_next to select each subsequent log by closest diameter.

  Args:
    logs: Dict of all available LogEntry objects keyed by index.
    indexes: List of available log indexes to select from.
    index: Index of the first log to place.
    pass_end: Pass end orientation for the first log.
    struct_l: Wall length in feet.

  Returns:
    A Layer object with 4 placed logs.
  """
  available = list(indexes)
  stack = []

  log = pick_first(logs, index, pass_end, struct_l)
  stack.append(log)
  available.remove(index)

  for _ in range(3):
    log = pick_next(log, logs, available, struct_l)
    stack.append(log)
    available.remove(log.index)

  remaining = [i for i in indexes if i not in [l.index for l in stack]]
  return Layer(indexes=remaining, stack=stack)


def build_first_layer(
  logs: dict[int, LogEntry],
  state: BuildState,
) -> Layer:
  """Build the first layer of the structure.

  Tries both THIN_END and FAT_END as the starting pass end,
  picks the one with the smallest corner connection distance.
  Always starts with the largest average diameter log.

  The connection distance is the absolute difference between
  the first and last log's corner diameters — smaller is better
  as it means the layer closes more level at the connection point.

  Args:
    logs: Dict of all available LogEntry objects keyed by index.
    state: Current build state with struct_l and remaining indexes.

  Returns:
    The best first Layer.

  Raises:
    ValueError: If fewer than 4 logs are available.
  """
  if len(logs) < 4:
    raise ValueError(
      f"Not enough logs to build first layer: {len(logs)} < 4"
    )

  # Start with the largest average diameter log
  all_indexes = sorted(
    logs.keys(),
    key=lambda i: -(logs[i].d_top + logs[i].d_butt) / 2
  )

  logger.debug(
    "build_first_layer: starting with log #%d (largest avg diameter)",
    all_indexes[0]
  )

  # Try both THIN and FAT end first
  results = {}
  for pass_end in [THIN_END, FAT_END]:
    layer = try_layer(
      logs=logs,
      indexes=all_indexes,
      index=all_indexes[0],
      pass_end=pass_end,
      struct_l=state.struct_l,
    )
    # Connection distance: difference between first and last log
    # corner diameters — measures how well the layer closes
    if pass_end == FAT_END:
      dist = abs(
        layer.stack[0].butt_new - layer.stack[3].butt_new
      )
    else:
      dist = abs(
        layer.stack[0].top_new - layer.stack[3].top_new
      )
    results[pass_end] = (layer, dist)
    logger.debug(
      "build_first_layer: pass_end=%s connection_distance=%.2f",
      "FAT" if pass_end == FAT_END else "THIN", dist
    )

  # Pick the pass end with smallest connection distance
  best_pass_end = min(results, key=lambda p: results[p][1])
  best_layer, best_dist = results[best_pass_end]

  logger.debug(
    "build_first_layer: selected %s END with distance=%.2f",
    "FAT" if best_pass_end == FAT_END else "THIN", best_dist
  )

  return best_layer
