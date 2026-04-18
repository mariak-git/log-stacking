# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Tests for the log selection functions in loghouse.selector."""

import logging
import pytest

from loghouse.config import FAT_END, THIN_END
from loghouse.models import Log, LogEntry
from loghouse.selector import pick_first, pick_next

@pytest.fixture
def log_capture(caplog):
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
