# Copyright 2015-2026 Maria Mercury <mariak>. All Rights Reserved.
"""Tests for the utility functions in loghouse.utils."""

import pytest

from loghouse.models import LogEntry
from loghouse.utils import avg_diameter


class TestAvgDiameter:
  """Tests for avg_diameter function."""

  def test_basic_average(self):
    """Correctly calculates average of d_top and d_butt."""
    entry = LogEntry(index=0, d_top=14.0, d_butt=18.0, length=35.0)
    assert avg_diameter(entry) == pytest.approx(16.0)

  def test_equal_diameters(self):
    """Returns correct average when d_top equals d_butt."""
    entry = LogEntry(index=0, d_top=15.0, d_butt=15.0, length=35.0)
    assert avg_diameter(entry) == pytest.approx(15.0)

  def test_larger_butt(self):
    """Correctly averages when d_butt is larger than d_top."""
    entry = LogEntry(index=0, d_top=10.0, d_butt=20.0, length=35.0)
    assert avg_diameter(entry) == pytest.approx(15.0)

  def test_fractional_average(self):
    """Correctly calculates fractional average."""
    entry = LogEntry(index=0, d_top=14.0, d_butt=19.0, length=35.0)
    assert avg_diameter(entry) == pytest.approx(16.5)
