# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Tests for the log selection functions in loghouse.selector."""

import logging
import pytest

from loghouse.selector import pick_first, pick_next, pick_layer_candidates
from loghouse.models import Log, LogEntry
from loghouse.config import FAT_END, THIN_END

@pytest.fixture
def log_capture(caplog: pytest.LogCaptureFixture):
  """Alias for caplog fixture to avoid confusion with CAPLOG LogType."""
  return caplog

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_logs(*specs) -> dict[int, LogEntry]:
  """Create a dict of LogEntry objects from tuples of 
  (index, d_top, d_butt, length)."""
  return {
    s[0]: LogEntry(index=s[0], d_top=s[1], d_butt=s[2], length=s[3])
    for s in specs
  }


# ------------------------------------------------------------------
# pick_first
# ------------------------------------------------------------------

class TestPickFirst:
  """Tests for pick_first function."""

  def test_returns_log(self):
    """pick_first returns a Log object."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    log = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    assert isinstance(log, Log)

  def test_correct_index(self):
    """Returned log has the correct index."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    log = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    assert log.index == 0

  def test_correct_pass_end_fat(self):
    """Returned log has FAT_END pass end when specified."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    log = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    assert log.pass_end == FAT_END

  def test_correct_pass_end_thin(self):
    """Returned log has THIN_END pass end when specified."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    log = pick_first(logs, index=0, pass_end=THIN_END, struct_l=33.0)
    assert log.pass_end == THIN_END

  def test_correct_struct_l(self):
    """Returned log carries the correct struct_l."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    log = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    assert log.struct_l == pytest.approx(33.0)

  def test_missing_index_raises(self):
    """KeyError is raised when index is not in logs."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    with pytest.raises(KeyError):
      pick_first(logs, index=99, pass_end=FAT_END, struct_l=33.0)

  def test_logger_debug_message(self, log_capture):
    """Logger emits debug message with log index and pass end."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    with log_capture.at_level(logging.DEBUG, logger="loghouse.selector"):
      pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    assert "pick_first" in log_capture.text
    assert "log #0" in log_capture.text
    assert "FAT_END" in log_capture.text


class TestPickNext:
  """Tests for pick_next function."""

  def test_returns_log(self):
    """pick_next returns a Log object."""
    logs = make_logs(
      (0, 14.0, 18.0, 35.0),
      (1, 14.5, 18.5, 35.0),
    )
    first = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    result = pick_next(first, logs, indexes=[1], struct_l=33.0)
    assert isinstance(result, Log)

  def test_alternates_pass_end_fat_to_thin(self):
    """Next log has THIN_END when current log has FAT_END."""
    logs = make_logs(
      (0, 14.0, 18.0, 35.0),
      (1, 14.5, 18.5, 35.0),
    )
    first = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    result = pick_next(first, logs, indexes=[1], struct_l=33.0)
    assert result.pass_end == THIN_END

  def test_alternates_pass_end_thin_to_fat(self):
    """Next log has FAT_END when current log has THIN_END."""
    logs = make_logs(
      (0, 14.0, 18.0, 35.0),
      (1, 14.5, 18.5, 35.0),
    )
    first = pick_first(logs, index=0, pass_end=THIN_END, struct_l=33.0)
    result = pick_next(first, logs, indexes=[1], struct_l=33.0)
    assert result.pass_end == FAT_END

  def test_picks_closest_diameter_fat_end(self):
    """Picks log with closest d_butt when current pass_end is FAT_END."""
    logs = make_logs(
      (0, 14.0, 18.0, 35.0),  # first log
      (1, 14.0, 18.1, 35.0),  # close butt match
      (2, 14.0, 22.0, 35.0),  # far butt match
    )
    first = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    result = pick_next(first, logs, indexes=[1, 2], struct_l=33.0)
    assert result.index == 1

  def test_picks_closest_diameter_thin_end(self):
    """Picks log with closest d_top when current pass_end is THIN_END."""
    logs = make_logs(
      (0, 14.0, 18.0, 35.0),  # first log
      (1, 14.1, 18.0, 35.0),  # close top match
      (2, 20.0, 24.0, 35.0),  # far top match
    )
    first = pick_first(logs, index=0, pass_end=THIN_END, struct_l=33.0)
    result = pick_next(first, logs, indexes=[1, 2], struct_l=33.0)
    assert result.index == 1

  def test_empty_indexes_raises(self):
    """ValueError is raised when indexes list is empty."""
    logs = make_logs((0, 14.0, 18.0, 35.0))
    first = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    with pytest.raises(ValueError, match="No remaining logs"):
      pick_next(first, logs, indexes=[], struct_l=33.0)

  def test_correct_struct_l(self):
    """Returned log carries the correct struct_l."""
    logs = make_logs(
      (0, 14.0, 18.0, 35.0),
      (1, 14.5, 18.5, 35.0),
    )
    first = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    result = pick_next(first, logs, indexes=[1], struct_l=33.0)
    assert result.struct_l == pytest.approx(33.0)

  def test_logger_debug_message(self, log_capture):
    """Logger emits debug message with matching info."""
    logs = make_logs(
      (0, 14.0, 18.0, 35.0),
      (1, 14.5, 18.5, 35.0),
    )
    first = pick_first(logs, index=0, pass_end=FAT_END, struct_l=33.0)
    with log_capture.at_level(logging.DEBUG, logger="loghouse.selector"):
      pick_next(first, logs, indexes=[1], struct_l=33.0)
    assert "pick_next" in log_capture.text
    assert "best match" in log_capture.text


class TestPickLayerCandidates:
  """Tests for pick_layer_candidates function."""

  # ------------------------------------------------------------------
  # Helpers
  # ------------------------------------------------------------------

  def make_logs_with_tapers(
      self, tapers: list[float], struct_l=33.0) -> dict[int, LogEntry]:
    """Create logs with specific tapers starting at index 4."""
    logs = {}
    for i, taper in enumerate(tapers):
      index = i + 4
      d_top = 14.0
      d_butt = round(d_top + taper * struct_l, 2)
      logs[index] = LogEntry(
        index=index, d_top=d_top, d_butt=d_butt, length=struct_l + 2.0
      )
    return logs

  # ------------------------------------------------------------------
  # Basic candidate selection
  # ------------------------------------------------------------------

  def test_returns_list(self, make_layer):
    """pick_layer_candidates returns a list."""
    layer = make_layer()
    logs = self.make_logs_with_tapers([0.12, 0.12, 0.12, 0.12, 0.12, 0.12])
    result = pick_layer_candidates(logs, layer)
    assert isinstance(result, list)

  def test_returns_at_least_4(self, make_layer):
    """Result always contains at least 4 candidates."""
    layer = make_layer()
    logs = self.make_logs_with_tapers([0.12, 0.12, 0.12, 0.12, 0.12, 0.12])
    result = pick_layer_candidates(logs, layer)
    assert len(result) >= 4

  def test_candidates_are_from_layer_indexes(self, make_layer):
    """All returned candidates are from layer.indexes."""
    layer = make_layer()
    logs = self.make_logs_with_tapers([0.12, 0.12, 0.12, 0.12, 0.12, 0.12])
    result = pick_layer_candidates(logs, layer)
    for i in result:
      assert i in layer.indexes

  def test_matches_by_taper(self, make_layer):
    """Logs with taper within margin are included as candidates."""
    layer = make_layer()
    # Get actual taper from layer to create a matching log
    wall_taper = list(layer.tapers.values())[0]
    # Create logs: first 4 match taper, last 2 don't
    tapers = [wall_taper] * 4 + [wall_taper + 1.0] * 2
    logs = self.make_logs_with_tapers(tapers)
    result = pick_layer_candidates(logs, layer, taper_margin=0.01)
    # Matching logs (indexes 4-7) should be in candidates
    for i in range(4, 8):
      assert i in result

  # ------------------------------------------------------------------
  # Fallback behavior
  # ------------------------------------------------------------------

  def test_fallback_when_few_matches(self, make_layer):
    """Falls back to priority queue when fewer than 4 taper matches."""
    layer = make_layer()
    # All logs have very different tapers — none will match
    logs = self.make_logs_with_tapers([5.0, 5.0, 5.0, 5.0, 5.0, 5.0])
    result = pick_layer_candidates(logs, layer, taper_margin=0.01)
    assert len(result) >= 4

  def test_fallback_prefers_larger_diameter(self, make_layer):
    """Fallback selects logs with larger average diameter first."""
    layer = make_layer()
    # No taper matches — all go to fallback
    # Make logs with very different diameters
    logs = {
      4: LogEntry(index=4, d_top=10.0, d_butt=12.0, length=35.0),  # small
      5: LogEntry(index=5, d_top=20.0, d_butt=24.0, length=35.0),  # large
      6: LogEntry(index=6, d_top=10.0, d_butt=12.0, length=35.0),  # small
      7: LogEntry(index=7, d_top=20.0, d_butt=24.0, length=35.0),  # large
      8: LogEntry(index=8, d_top=10.0, d_butt=12.0, length=35.0),  # small
      9: LogEntry(index=9, d_top=10.0, d_butt=12.0, length=35.0),  # small
    }
    result = pick_layer_candidates(logs, layer, taper_margin=0.01)
    # Large diameter logs (5, 7) should be preferred
    assert 5 in result
    assert 7 in result

  # ------------------------------------------------------------------
  # Error handling
  # ------------------------------------------------------------------

  def test_too_few_logs_raises(self, make_layer):
    """ValueError raised when fewer than 4 logs remain."""
    layer = make_layer()
    # Override indexes to have only 3
    layer.indexes = [4, 5, 6]
    logs = self.make_logs_with_tapers([0.12, 0.12, 0.12])
    with pytest.raises(ValueError, match="Not enough logs remaining"):
      pick_layer_candidates(logs, layer)

  # ------------------------------------------------------------------
  # Logger
  # ------------------------------------------------------------------

  def test_logger_debug_message(self, log_capture, make_layer):
    """Logger emits debug message with candidate count."""
    layer = make_layer()
    logs = self.make_logs_with_tapers([0.12, 0.12, 0.12, 0.12, 0.12, 0.12])
    with log_capture.at_level(logging.DEBUG, logger="loghouse.selector"):
      pick_layer_candidates(logs, layer)
    assert "pick_layer_candidates" in log_capture.text
    assert "candidates" in log_capture.text
