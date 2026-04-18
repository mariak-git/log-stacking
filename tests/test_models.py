# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.
"""Tests for the Log and Layer models in loghouse.models."""

import pytest
from loghouse.config import (THIN_END, FAT_END, SW, NW, NE, SE, NORTH, WEST,
                             EAST, SOUTH)
from loghouse.models import LogEntry, Log, Layer


class TestLogEntry:
  """Tests for the LogEntry dataclass."""

  def test_valid_construction(self):
    """A valid log entry is created without errors."""
    log = LogEntry(index=1, d_top=14.0, d_butt=18.0, length=35.0)
    assert log.index == 1
    assert log.d_top == 14.0
    assert log.d_butt == 18.0
    assert log.length == 35.0

  def test_taper_calculation(self):
    """Taper is correctly calculated as (d_butt - d_top) / length."""
    log = LogEntry(index=1, d_top=14.0, d_butt=18.0, length=40.0)
    assert log.taper == pytest.approx(0.1)

  def test_zero_taper(self):
    """A log with equal top and butt diameters has zero taper."""
    log = LogEntry(index=1, d_top=15.0, d_butt=15.0, length=35.0)
    assert log.taper == pytest.approx(0.0)

  def test_invalid_length_zero(self):
    """A log with zero length raises ValueError."""
    with pytest.raises(ValueError, match="length must be positive"):
      LogEntry(index=1, d_top=14.0, d_butt=18.0, length=0.0)

  def test_invalid_length_negative(self):
    """A log with negative length raises ValueError."""
    with pytest.raises(ValueError, match="length must be positive"):
      LogEntry(index=1, d_top=14.0, d_butt=18.0, length=-5.0)

  def test_invalid_negative_diameter(self):
    """A log with negative diameter raises ValueError."""
    with pytest.raises(ValueError, match="diameters must be non-negative"):
      LogEntry(index=1, d_top=-1.0, d_butt=18.0, length=35.0)

  def test_invalid_butt_smaller_than_top(self):
    """A log where d_butt < d_top raises ValueError."""
    with pytest.raises(ValueError, match="d_butt must be >= d_top"):
      LogEntry(index=1, d_top=18.0, d_butt=14.0, length=35.0)


class TestLog:
  """Tests for the Log class."""

  # ------------------------------------------------------------------
  # Fixtures — reusable LogEntry objects
  # ------------------------------------------------------------------

  def make_entry(self, index=1, d_top=14.0, d_butt=18.0, length=35.0):
    """Helper to create a LogEntry with sensible defaults."""
    return LogEntry(index=index, d_top=d_top, d_butt=d_butt, length=length)

  # ------------------------------------------------------------------
  # Construction
  # ------------------------------------------------------------------

  def test_valid_construction_fat_end(self):
    """A log placed with FAT_END pass is created without errors."""
    entry = self.make_entry()
    log = Log(entry=entry, pass_end=FAT_END, struct_l=33.0)
    assert log.index == 1
    assert log.pass_end == FAT_END
    assert log.pass_str == "FAT_END"
    assert log.struct_l == 33.0

  def test_valid_construction_thin_end(self):
    """A log placed with THIN_END pass is created without errors."""
    entry = self.make_entry()
    log = Log(entry=entry, pass_end=THIN_END, struct_l=33.0)
    assert log.pass_end == THIN_END
    assert log.pass_str == "THIN_END"

  def test_too_short_raises(self):
    """A log shorter than struct_l raises ValueError."""
    entry = self.make_entry(length=30.0)
    with pytest.raises(ValueError, match="shorter than struct_l"):
      Log(entry=entry, pass_end=FAT_END, struct_l=33.0)

  def test_exact_length_does_not_raise(self):
    """A log exactly equal to struct_l is valid (zero overdangle)."""
    entry = self.make_entry(length=33.0)
    log = Log(entry=entry, pass_end=FAT_END, struct_l=33.0)
    assert log.overdangle == pytest.approx(0.0)

  # ------------------------------------------------------------------
  # Overdangle
  # ------------------------------------------------------------------

  def test_overdangle_calculation(self):
    """Overdangle is correctly calculated as length - struct_l."""
    entry = self.make_entry(length=35.0)
    log = Log(entry=entry, pass_end=FAT_END, struct_l=33.0)
    assert log.overdangle == pytest.approx(2.0)

  # ------------------------------------------------------------------
  # Adjusted end diameters
  # ------------------------------------------------------------------

  def test_fat_end_butt_adjusted(self):
    """With FAT_END pass, butt_new is trimmed by overdangle * taper."""
    entry = self.make_entry(d_top=14.0, d_butt=18.0, length=35.0)
    log = Log(entry=entry, pass_end=FAT_END, struct_l=33.0)
    expected_butt_new = 18.0 - 2.0 * entry.taper
    assert log.butt_new == pytest.approx(expected_butt_new)
    assert log.top_new == pytest.approx(14.0)  # top unchanged

  def test_thin_end_top_adjusted(self):
    """With THIN_END pass, top_new is adjusted upward by overdangle * taper."""
    entry = self.make_entry(d_top=14.0, d_butt=18.0, length=35.0)
    log = Log(entry=entry, pass_end=THIN_END, struct_l=33.0)
    expected_top_new = 14.0 + 2.0 * entry.taper
    assert log.top_new == pytest.approx(expected_top_new)
    assert log.butt_new == pytest.approx(18.0)  # butt unchanged

  def test_zero_overdangle_no_adjustment(self):
    """With zero overdangle, top_new and butt_new equal original values."""
    entry = self.make_entry(length=33.0)
    log = Log(entry=entry, pass_end=FAT_END, struct_l=33.0)
    assert log.top_new == pytest.approx(entry.d_top)
    assert log.butt_new == pytest.approx(entry.d_butt)

  # ------------------------------------------------------------------
  # get_corner_diameter
  # ------------------------------------------------------------------

  def test_corner_diameter_fat_end(self):
    """With FAT_END pass, corner diameter is butt_new."""
    entry = self.make_entry(d_top=14.0, d_butt=18.0, length=35.0)
    log = Log(entry=entry, pass_end=FAT_END, struct_l=33.0)
    assert log.get_corner_diameter() == pytest.approx(log.butt_new)

  def test_corner_diameter_thin_end(self):
    """With THIN_END pass, corner diameter is top_new."""
    entry = self.make_entry(d_top=14.0, d_butt=18.0, length=35.0)
    log = Log(entry=entry, pass_end=THIN_END, struct_l=33.0)
    assert log.get_corner_diameter() == pytest.approx(log.top_new)

  # ------------------------------------------------------------------
  # __repr__
  # ------------------------------------------------------------------

  def test_repr_contains_index(self):
    """repr includes the log index."""
    entry = self.make_entry(index=7)
    log = Log(entry=entry, pass_end=FAT_END, struct_l=33.0)
    assert "index=7" in repr(log)


class TestLayer:
  """Tests for the Layer class."""

  # ------------------------------------------------------------------
  # Helpers
  # ------------------------------------------------------------------

  def make_entry(self, index, d_top, d_butt, length):
    """Create a LogEntry with given dimensions."""
    return LogEntry(index=index, d_top=d_top, d_butt=d_butt, length=length)

  def make_log(self,
               entry: LogEntry,
               pass_end: int,
               struct_l: float = 33.0) -> Log:
    """Create a placed Log from a LogEntry."""
    return Log(entry=entry, pass_end=pass_end, struct_l=struct_l)

  def make_layer(self, struct_l=33.0):
    """Create a minimal valid Layer with 4 logs alternating pass ends."""
    e0 = self.make_entry(0, 14.0, 18.0, 35.0)
    e1 = self.make_entry(1, 14.5, 18.5, 35.0)
    e2 = self.make_entry(2, 15.0, 19.0, 35.0)
    e3 = self.make_entry(3, 15.5, 19.5, 35.0)
    logs = [
        self.make_log(e0, THIN_END, struct_l),
        self.make_log(e1, FAT_END, struct_l),
        self.make_log(e2, THIN_END, struct_l),
        self.make_log(e3, FAT_END, struct_l),
    ]
    return Layer(indexes=[4, 5, 6, 7], stack=logs)

  # ------------------------------------------------------------------
  # Construction
  # ------------------------------------------------------------------

  def test_valid_construction(self):
    """A valid layer is created without errors."""
    layer = self.make_layer()
    assert len(layer.stack) == 4
    assert len(layer.indexes) == 4

  def test_wrong_stack_size_raises(self):
    """A stack with fewer than 4 logs raises ValueError."""
    e0 = self.make_entry(0, 14.0, 18.0, 35.0)
    e1 = self.make_entry(1, 14.5, 18.5, 35.0)
    logs = [
        self.make_log(e0, THIN_END),
        self.make_log(e1, FAT_END),
    ]
    with pytest.raises(ValueError, match="exactly 4 logs"):
      Layer(indexes=[], stack=logs)

  def test_struct_l_carried_from_logs(self):
    """Layer carries struct_l from the first log."""
    layer = self.make_layer(struct_l=35.0)
    assert layer.struct_l == pytest.approx(35.0)

  # ------------------------------------------------------------------
  # Corners
  # ------------------------------------------------------------------

  def test_corners_keys(self):
    """Layer corners dict has all 4 corner keys."""
    layer = self.make_layer()
    assert set(layer.corners.keys()) == {SW, NW, NE, SE}

  def test_corners_are_positive(self):
    """All corner heights are positive."""
    layer = self.make_layer()
    for corner, value in layer.corners.items():
      assert value > 0, f"Corner {corner} height should be positive"

  def test_corner_is_max_of_two_logs(self):
    """Each corner height is the max of the two meeting log diameters."""
    layer = self.make_layer()
    # SW corner: log0 (THIN_END) meets log3 (FAT_END)
    log1 = layer.stack[SW]
    log2 = layer.stack[(SW + len(layer.stack) - 1) % len(layer.stack)]
    c1 = log1.get_corner_diameter()
    # log1 is THIN_END so log2 presents top_new
    c2 = log2.top_new
    assert layer.corners[SW] == pytest.approx(max(c1, c2))

  # ------------------------------------------------------------------
  # Tapers
  # ------------------------------------------------------------------

  def test_tapers_keys(self):
    """Layer tapers dict has all 4 wall direction keys."""
    layer = self.make_layer()
    assert set(layer.tapers.keys()) == {NORTH, SOUTH, EAST, WEST}

  def test_tapers_are_non_negative(self):
    """All wall tapers are non-negative."""
    layer = self.make_layer()
    for direction, value in layer.tapers.items():
      assert value >= 0, f"Taper for {direction} should be non-negative"

  def test_north_taper_calculation(self):
    """North taper is abs(SW corner - NW corner) / struct_l."""
    layer = self.make_layer()
    expected = abs(layer.corners[SW] - layer.corners[NW]) / layer.struct_l
    assert layer.tapers[NORTH] == pytest.approx(expected)

  # ------------------------------------------------------------------
  # validate_indexes
  # ------------------------------------------------------------------

  def test_validate_indexes_passes(self):
    """validate_indexes passes when no stack log is in indexes."""
    layer = self.make_layer()
    layer.validate_indexes()  # should not raise

  def test_validate_indexes_raises(self):
    """validate_indexes raises if a stack log index appears in indexes."""
    e0 = self.make_entry(0, 14.0, 18.0, 35.0)
    e1 = self.make_entry(1, 14.5, 18.5, 35.0)
    e2 = self.make_entry(2, 15.0, 19.0, 35.0)
    e3 = self.make_entry(3, 15.5, 19.5, 35.0)
    logs = [
        self.make_log(e0, THIN_END),
        self.make_log(e1, FAT_END),
        self.make_log(e2, THIN_END),
        self.make_log(e3, FAT_END),
    ]
    # index 2 is both in stack and indexes — should fail
    with pytest.raises(ValueError,
                       match="both the stack and remaining indexes"):
      layer = Layer(indexes=[2, 5, 6, 7], stack=logs)
      layer.validate_indexes()
