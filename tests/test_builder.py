# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Tests for the layer building functions in loghouse.builder."""

import math

import pytest

from loghouse.builder import BuildState, try_layer
from loghouse.config import SW, NW, NE, SE
from loghouse.models import LogEntry, Log, Layer
from loghouse.config import THIN_END, FAT_END


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_layer(struct_l=33.0) -> Layer:
  """Create a minimal valid Layer with 4 logs."""
  logs = {
    0: LogEntry(index=0, d_top=14.0, d_butt=18.0, length=35.0),
    1: LogEntry(index=1, d_top=14.5, d_butt=18.5, length=35.0),
    2: LogEntry(index=2, d_top=15.0, d_butt=19.0, length=35.0),
    3: LogEntry(index=3, d_top=15.5, d_butt=19.5, length=35.0),
  }
  stack = [
    Log(entry=logs[0], pass_end=THIN_END, struct_l=struct_l),
    Log(entry=logs[1], pass_end=FAT_END,  struct_l=struct_l),
    Log(entry=logs[2], pass_end=THIN_END, struct_l=struct_l),
    Log(entry=logs[3], pass_end=FAT_END,  struct_l=struct_l),
  ]
  return Layer(indexes=[4, 5, 6, 7], stack=stack)


# ------------------------------------------------------------------
# BuildState
# ------------------------------------------------------------------

class TestBuildState:
  """Tests for the BuildState dataclass."""

  def test_default_corner_heights(self):
    """Corner heights default to zero."""
    state = BuildState(struct_l=33.0)
    assert state.corner_heights == {SW: 0.0, NW: 0.0, NE: 0.0, SE: 0.0}

  def test_default_target_height(self):
    """Default target height is 18*10 inches."""
    state = BuildState(struct_l=33.0)
    assert state.target_height == pytest.approx(18 * 10)

  def test_default_level_margin(self):
    """Default level margin is 1.5 inches."""
    state = BuildState(struct_l=33.0)
    assert state.level_margin == pytest.approx(1.5)

  def test_default_taper_margin(self):
    """Default taper margin is 0.01."""
    state = BuildState(struct_l=33.0)
    assert state.taper_margin == pytest.approx(0.01)

  def test_default_layers_empty(self):
    """Layers list defaults to empty."""
    state = BuildState(struct_l=33.0)
    assert not state.layers

  # ------------------------------------------------------------------
  # update_corner_heights
  # ------------------------------------------------------------------

  def test_update_corner_heights(self):
    """Corner heights are correctly accumulated after adding a layer."""
    state = BuildState(struct_l=33.0)
    layer = make_layer()
    state.update_corner_heights(layer)
    for corner in [SW, NW, NE, SE]:
      assert state.corner_heights[corner] == pytest.approx(
        layer.corners[corner]
      )

  def test_update_corner_heights_accumulates(self):
    """Corner heights accumulate correctly across multiple layers."""
    state = BuildState(struct_l=33.0)
    layer = make_layer()
    state.update_corner_heights(layer)
    state.update_corner_heights(layer)
    for corner in [SW, NW, NE, SE]:
      assert state.corner_heights[corner] == pytest.approx(
        layer.corners[corner] * 2
      )

  # ------------------------------------------------------------------
  # is_level
  # ------------------------------------------------------------------

  def test_is_level_true_when_equal(self):
    """is_level returns True when all corners are equal."""
    state = BuildState(struct_l=33.0, level_margin=1.5)
    state.corner_heights = {SW: 10.0, NW: 10.0, NE: 10.0, SE: 10.0}
    assert state.is_level() is True

  def test_is_level_true_within_margin(self):
    """is_level returns True when difference is within margin."""
    state = BuildState(struct_l=33.0, level_margin=1.5)
    state.corner_heights = {SW: 10.0, NW: 11.0, NE: 10.5, SE: 11.0}
    assert state.is_level() is True

  def test_is_level_false_outside_margin(self):
    """is_level returns False when difference exceeds margin."""
    state = BuildState(struct_l=33.0, level_margin=1.5)
    state.corner_heights = {SW: 10.0, NW: 12.0, NE: 10.0, SE: 10.0}
    assert state.is_level() is False

  # ------------------------------------------------------------------
  # is_target_reached
  # ------------------------------------------------------------------

  def test_is_target_reached_false_initially(self):
    """is_target_reached returns False when corners are at zero."""
    state = BuildState(struct_l=33.0, target_height=180.0)
    assert state.is_target_reached() is False

  def test_is_target_reached_true(self):
    """is_target_reached returns True when max corner >= target."""
    state = BuildState(struct_l=33.0, target_height=180.0)
    state.corner_heights = {SW: 180.0, NW: 179.0, NE: 178.0, SE: 177.0}
    assert state.is_target_reached() is True

  def test_is_target_reached_false_below_target(self):
    """is_target_reached returns False when max corner < target."""
    state = BuildState(struct_l=33.0, target_height=180.0)
    state.corner_heights = {SW: 170.0, NW: 168.0, NE: 169.0, SE: 167.0}
    assert state.is_target_reached() is False

  # ------------------------------------------------------------------
  # corner_std_dev
  # ------------------------------------------------------------------

  def test_std_dev_zero_when_equal(self):
    """std_dev is zero when all corners are equal."""
    state = BuildState(struct_l=33.0)
    state.corner_heights = {SW: 10.0, NW: 10.0, NE: 10.0, SE: 10.0}
    assert state.corner_std_dev() == pytest.approx(0.0)

  def test_std_dev_correct(self):
    """std_dev is correctly calculated."""
    state = BuildState(struct_l=33.0)
    state.corner_heights = {SW: 10.0, NW: 12.0, NE: 10.0, SE: 12.0}
    heights = [10.0, 12.0, 10.0, 12.0]
    mean = sum(heights) / 4
    expected = math.sqrt(sum((h - mean) ** 2 for h in heights) / 4)
    assert state.corner_std_dev() == pytest.approx(expected)

  # ------------------------------------------------------------------
  # __repr__
  # ------------------------------------------------------------------

  def test_repr_contains_layer_count(self):
    """repr contains the number of layers."""
    state = BuildState(struct_l=33.0)
    assert "layers=0" in repr(state)


# ------------------------------------------------------------------
# Helpers (add to existing helpers section)
# ------------------------------------------------------------------

def make_logs(count: int, struct_l: float = 33.0) -> dict[int, LogEntry]:
  """Create a dict of LogEntry objects with gradually increasing dimensions."""
  logs = {}
  for i in range(count):
    d_top = round(14.0 + i * 0.5, 2)
    d_butt = round(d_top + 4.0, 2)
    logs[i] = LogEntry(
      index=i,
      d_top=d_top,
      d_butt=d_butt,
      length=struct_l + 2.0
    )
  return logs


class TestTryLayer:
  """Tests for try_layer function."""

  def test_returns_layer(self):
    """try_layer returns a Layer object."""
    logs = make_logs(8)
    indexes = list(range(8))
    result = try_layer(logs, indexes, index=0, pass_end=FAT_END, struct_l=33.0)
    assert isinstance(result, Layer)

  def test_layer_has_4_logs(self):
    """Layer stack contains exactly 4 logs."""
    logs = make_logs(8)
    indexes = list(range(8))
    result = try_layer(logs, indexes, index=0, pass_end=FAT_END, struct_l=33.0)
    assert len(result.stack) == 4

  def test_first_log_has_correct_index(self):
    """First log in stack has the specified start index."""
    logs = make_logs(8)
    indexes = list(range(8))
    result = try_layer(logs, indexes, index=2, pass_end=FAT_END, struct_l=33.0)
    assert result.stack[0].index == 2

  def test_first_log_has_correct_pass_end(self):
    """First log has the specified pass end."""
    logs = make_logs(8)
    indexes = list(range(8))
    result = try_layer(logs, indexes, index=0, pass_end=FAT_END, struct_l=33.0)
    assert result.stack[0].pass_end == FAT_END

  def test_pass_end_alternates(self):
    """Pass end alternates across the 4 logs in the stack."""
    logs = make_logs(8)
    indexes = list(range(8))
    result = try_layer(logs, indexes, index=0, pass_end=FAT_END, struct_l=33.0)
    assert result.stack[0].pass_end == FAT_END
    assert result.stack[1].pass_end == THIN_END
    assert result.stack[2].pass_end == FAT_END
    assert result.stack[3].pass_end == THIN_END

  def test_remaining_indexes_correct(self):
    """Remaining indexes exclude the 4 selected logs."""
    logs = make_logs(8)
    indexes = list(range(8))
    result = try_layer(logs, indexes, index=0, pass_end=FAT_END, struct_l=33.0)
    used = {log.index for log in result.stack}
    assert len(result.indexes) == 4
    for i in result.indexes:
      assert i not in used

  def test_validate_indexes_passes(self):
    """No selected log appears in remaining indexes."""
    logs = make_logs(8)
    indexes = list(range(8))
    result = try_layer(logs, indexes, index=0, pass_end=FAT_END, struct_l=33.0)
    result.validate_indexes()  # should not raise

  def test_not_enough_logs_raises(self):
    """ValueError raised when fewer than 4 logs available."""
    logs = make_logs(3)
    indexes = list(range(3))
    with pytest.raises(Exception):
      try_layer(logs, indexes, index=0, pass_end=FAT_END, struct_l=33.0)
