# Copyright 2015-2026 Maria Mercury <mariak>. All Rights Reserved.

"""Layer building functions for the log house stacking algorithm.

Builds layers of logs using a greedy algorithm with exhaustive
combination search for optimal corner leveling.

# TODO(mariak): Implement lookahead algorithm as an alternative
# to the greedy approach for better global optimization.
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations

from loghouse.config import (
  FAT_END,
  THIN_END,
  CORNERS,
  SW, NW, NE, SE,
)
from loghouse.models import LogEntry, Layer
from loghouse.selector import pick_first, pick_next, pick_layer_candidates
from loghouse.utils import avg_diameter

logger = logging.getLogger(__name__)

# Default target height: 10 courses at 18 inches each, converted to feet
_DEFAULT_TARGET_HEIGHT_FT = (18 * 10) / 12

class ScoringMethod(Enum):
  """Scoring method for layer combination selection.

  STD_DEV: Minimize standard deviation of cumulative corner heights.
    Used for even layers to enforce leveling.
  CONNECTION_DIST: Minimize corner connection distance.
    Used for odd layers.

  # TODO(mariak): Add lookahead scoring method for global optimization.
  """
  STD_DEV = "std_dev"
  CONNECTION_DIST = "connection_dist"

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
    key=lambda i: -avg_diameter(logs[i])
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


def _score_layer(
  layer: Layer,
  state: BuildState,
  scoring: ScoringMethod,
  pass_end: int = FAT_END,
) -> float:
  """Score a candidate layer using the given scoring method.

  Args:
    layer: The candidate layer to score.
    state: Current build state with cumulative corner heights.
    scoring: Scoring method to use.
    pass_end: Pass end orientation for connection distance scoring.

  Returns:
    Score value — lower is better.
  """
  if scoring == ScoringMethod.STD_DEV:
    heights = [
      state.corner_heights[corner] + layer.corners[corner]
      for corner in CORNERS
    ]
    mean = sum(heights) / len(heights)
    variance = sum((h - mean) ** 2 for h in heights) / len(heights)
    return math.sqrt(variance)

  if scoring == ScoringMethod.CONNECTION_DIST:
    if pass_end == FAT_END:
      return abs(layer.stack[0].butt_new - layer.stack[3].butt_new)
    return abs(layer.stack[0].top_new - layer.stack[3].top_new)

  raise ValueError(f"Unknown scoring method: {scoring}")


def build_layer(
  logs: dict[int, LogEntry],
  prev_layer: Layer,
  pass_end: int,
  state: BuildState,
  scoring: ScoringMethod,
) -> Layer:
  """Build the next layer by trying all C(n,4) candidate combinations.

  Selects the best combination of 4 logs from candidates based on
  the scoring method:
  - STD_DEV: minimizes std_dev of cumulative corner heights (even layers)
  - CONNECTION_DIST: minimizes corner connection distance (odd layers)

  Within each combination, logs are selected greedily using pick_next.

  # TODO(mariak): Add cap on candidate set size for performance
  # with large catalogues e.g. max 10 candidates.
  # TODO(mariak): Add early termination when std_dev == 0.0.
  # TODO(mariak): Consider caching pick_next results across combinations.

  Args:
    logs: Dict of all available LogEntry objects keyed by index.
    prev_layer: The previously built layer.
    pass_end: Pass end orientation for this layer.
    state: Current build state with struct_l and corner heights.
    scoring: Scoring method to use for combination selection.

  Returns:
    The best Layer found across all combinations.

  Raises:
    ValueError: If fewer than 4 candidate logs are available.
  """
  candidates = pick_layer_candidates(
    logs, prev_layer, state.taper_margin
  )

  if len(candidates) < 4:
    raise ValueError(
      f"Not enough candidates for next layer: {len(candidates)} < 4"
    )

  logger.debug(
    "build_layer: trying C(%d,4)=%d combinations with scoring=%s",
    len(candidates),
    len(list(combinations(candidates, 4))),
    scoring.value
  )

  best_layer = None
  best_score = float("inf")

  for combo in combinations(candidates, 4):
    # Within combo, start with largest avg diameter log
    start_index = max(
      combo,
      key=lambda i: avg_diameter(logs[i])
    )
    layer = try_layer(
      logs=logs,
      indexes=list(combo),
      index=start_index,
      pass_end=pass_end,
      struct_l=state.struct_l,
    )

    score = _score_layer(layer, state, scoring, pass_end)

    if score < best_score:
      best_score = score
      best_layer = layer

  logger.debug(
    "build_layer: best score=%.4f with logs=%s",
    best_score,
    [log.index for log in best_layer.stack]
  )

  # Update remaining indexes — remove used logs from prev_layer.indexes
  best_layer.indexes = [
    i for i in prev_layer.indexes
    if i not in {log.index for log in best_layer.stack}
  ]

  return best_layer
