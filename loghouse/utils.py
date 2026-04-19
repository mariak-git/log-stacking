# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Utility functions for the log house stacking algorithm."""

from loghouse.models import LogEntry


def avg_diameter(entry: LogEntry) -> float:
  """Calculate the average diameter of a log entry.

  The average diameter is used as a proxy for log size when
  selecting larger logs for lower layers.

  Args:
    entry: The log entry to calculate average diameter for.

  Returns:
    Average of d_top and d_butt in inches.
  """
  return (entry.d_top + entry.d_butt) / 2
