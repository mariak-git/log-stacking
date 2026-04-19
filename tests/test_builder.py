# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Tests for the layer building functions in loghouse.builder."""

import math

import pytest

from loghouse.builder import BuildState
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
