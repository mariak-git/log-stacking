# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Shared pytest fixtures available to all test modules in the test suite."""

import pytest

from loghouse.config import THIN_END, FAT_END
from loghouse.models import LogEntry, Log, Layer


@pytest.fixture
def make_layer():
  """Factory fixture to create a minimal valid Layer."""
  def _make_layer(struct_l=33.0):
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
  return _make_layer
