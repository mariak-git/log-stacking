# Copyright 2015-2026 Maria Mercury <mariak>. All Rights Reserved.
"""Integration tests for the log house stacking application."""

import io
import os
import random
import sys
import tempfile
import time

import pytest

from loghouse.cli import main

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def random_catalogue_path():
  """Generate a random log catalogue CSV and return its path.

  Uses timestamp-based seed for varied test runs while remaining
  reproducible within a single test session.
  """

  def _generate(
    seed: int = int(time.time()),
    nlayers: int = 6,
    min_top: float = 18.0,
    min_len: float = 36.0,
    taper: float = 0.15,
  ) -> str:
    random.seed(seed)
    rows = ["index,d_top,d_butt,length,notes,log_type"]
    count = int(nlayers * min_top / 12 * 4)
    for i in range(count):
      length = round(random.uniform(min_len, 37), 2)
      d_top = round(random.uniform(min_top, min_top + 1.6), 2)
      d_butt = round(random.uniform(d_top + taper * length, d_top + 5), 2)
      rows.append(f"{i},{d_top},{d_butt},{length},,WALL")
    content = "\n".join(rows)

    with tempfile.NamedTemporaryFile(
      mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as f:
      f.write(content)
      return f.name

  path = _generate()
  yield path
  os.unlink(path)


@pytest.fixture
def capture_stdout():
  """Fixture to capture stdout output from main()."""
  def _run(args: list[str]) -> str:
    captured = io.StringIO()
    sys_stdout = sys.stdout
    sys.stdout = captured
    try:
      main(args)
    finally:
      sys.stdout = sys_stdout
    return captured.getvalue()
  return _run


# ------------------------------------------------------------------
# Integration tests
# ------------------------------------------------------------------

class TestIntegration:
  """End-to-end integration tests for the log stacking application."""

  DEFAULT_ARGS = [
    "--length", "33",
    "--height", "6.0",
    "--no-catalogue",
  ]

  def test_runs_without_error(self, random_catalogue_path, capture_stdout):
    """Application runs without raising exceptions."""
    capture_stdout([
      "--logfile", random_catalogue_path,
      *self.DEFAULT_ARGS,
    ])

  def test_output_contains_layer1(self, random_catalogue_path, capture_stdout):
    """Output contains at least one layer."""
    output = capture_stdout([
      "--logfile", random_catalogue_path,
      *self.DEFAULT_ARGS,
    ])
    assert "LAYER #1" in output

  def test_output_contains_summary(self, random_catalogue_path, capture_stdout):
    """Output contains summary section."""
    output = capture_stdout([
      "--logfile", random_catalogue_path,
      *self.DEFAULT_ARGS,
    ])
    assert "SUMMARY" in output

  def test_output_contains_total_layers(
      self, random_catalogue_path, capture_stdout):
    """Output summary contains total layers count."""
    output = capture_stdout([
      "--logfile", random_catalogue_path,
      *self.DEFAULT_ARGS,
    ])
    assert "Total layers:" in output

  def test_height_within_tolerance(self, random_catalogue_path, capture_stdout):
    """Actual height is within tolerance of target height."""
    target_height_ft = 6.0
    target_height_in = target_height_ft * 12
    height_tolerance = 10.0
    output = capture_stdout([
      "--logfile", random_catalogue_path,
      "--length", "33",
      "--height", str(target_height_ft),
      "--height-tolerance", str(height_tolerance),
      "--no-catalogue",
    ])
    for line in output.splitlines():
      if "Actual height:" in line:
        parts = line.split()
        feet = float(parts[2])
        inches = float(parts[4])
        actual_height_in = feet * 12 + inches
        assert abs(actual_height_in - target_height_in) <= height_tolerance
        return
    pytest.fail("Actual height not found in output")

  def test_catalogue_printed_by_default(
    self, random_catalogue_path, capture_stdout
  ):
    """Catalogue is printed when --no-catalogue is not specified."""
    output = capture_stdout([
      "--logfile", random_catalogue_path,
      "--length", "33",
      "--height", "12.0",
    ])
    assert "WALL LOGS CATALOGUE" in output

  def test_catalogue_not_printed_with_flag(
    self, random_catalogue_path, capture_stdout
  ):
    """Catalogue is not printed when --no-catalogue is specified."""
    output = capture_stdout([
      "--logfile", random_catalogue_path,
      *self.DEFAULT_ARGS,
    ])
    assert "WALL LOGS CATALOGUE" not in output

  def test_deterministic_output(self, random_catalogue_path, capture_stdout):
    """Same seed produces same number of layers."""
    output1 = capture_stdout([
      "--logfile", random_catalogue_path,
      *self.DEFAULT_ARGS,
    ])
    output2 = capture_stdout([
      "--logfile", random_catalogue_path,
      *self.DEFAULT_ARGS,
    ])
    layers1 = next(
      line for line in output1.splitlines()
      if "Total layers:" in line
    )
    layers2 = next(
      line for line in output2.splitlines()
      if "Total layers:" in line
    )
    assert layers1 == layers2
