# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Tests for the printer module in loghouse.printer."""

import io
import sys

from loghouse.builder import BuildState
from loghouse.catalogue import CatalogueEntry, LogType
from loghouse.config import SW, NW, NE, SE
from loghouse.models import LogEntry
from loghouse.printer import (
  print_catalogue,
  print_layer,
  print_summary,
  get_writer,
  _feet_and_inches,
  _format_notes,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_writer() -> io.StringIO:
  """Create an in-memory writer for capturing output."""
  return io.StringIO()


def make_catalogue() -> dict:
  """Create a small test catalogue."""
  return {
    0: CatalogueEntry(
      LogEntry(0, 14.0, 18.0, 35.0), {LogType.WALL}, "straight"
    ),
    1: CatalogueEntry(
      LogEntry(1, 14.5, 18.5, 36.0), {LogType.WALL}, "bowed"
    ),
    2: CatalogueEntry(
      LogEntry(2, 15.0, 19.0, 35.5), {LogType.WALL}, ""
    ),
  }


# ------------------------------------------------------------------
# _feet_and_inches
# ------------------------------------------------------------------

class TestFeetAndInches:
  """Tests for _feet_and_inches helper."""

  def test_exact_feet(self):
    """Converts exact feet correctly."""
    assert _feet_and_inches(24.0) == "2 ft 0.0 in"

  def test_feet_and_inches(self):
    """Converts feet and inches correctly."""
    assert _feet_and_inches(15.0) == "1 ft 3.0 in"

  def test_inches_only(self):
    """Converts inches only correctly."""
    assert _feet_and_inches(6.0) == "0 ft 6.0 in"

  def test_fractional_inches(self):
    """Converts fractional inches correctly."""
    assert _feet_and_inches(12.5) == "1 ft 0.5 in"


# ------------------------------------------------------------------
# _format_notes
# ------------------------------------------------------------------

class TestFormatNotes:
  """Tests for _format_notes helper."""

  def test_straight_keyword(self):
    """Returns formatted string for 'straight'."""
    assert _format_notes("straight") == "  [straight]"

  def test_bowed_keyword(self):
    """Returns formatted string for 'bowed'."""
    assert _format_notes("bowed") == "  [bowed]"

  def test_crooked_keyword(self):
    """Returns formatted string for 'crooked'."""
    assert _format_notes("crooked") == "  [crooked]"

  def test_no_keyword(self):
    """Returns empty string when no keyword present."""
    assert _format_notes("good log") == ""

  def test_empty_notes(self):
    """Returns empty string for empty notes."""
    assert _format_notes("") == ""

  def test_case_insensitive(self):
    """Keyword matching is case insensitive."""
    assert _format_notes("Straight") == "  [Straight]"


# ------------------------------------------------------------------
# print_catalogue
# ------------------------------------------------------------------

class TestPrintCatalogue:
  """Tests for print_catalogue function."""

  def test_prints_header(self):
    """Output contains catalogue header."""
    writer = make_writer()
    catalogue = make_catalogue()
    print_catalogue(catalogue, list(catalogue.keys()), writer)
    output = writer.getvalue()
    assert "WALL LOGS CATALOGUE" in output

  def test_prints_column_headers(self):
    """Output contains column headers."""
    writer = make_writer()
    catalogue = make_catalogue()
    print_catalogue(catalogue, list(catalogue.keys()), writer)
    output = writer.getvalue()
    assert "Top (in)" in output
    assert "Butt (in)" in output
    assert "Length (ft)" in output
    assert "Taper (in)" in output

  def test_prints_log_numbers(self):
    """Output contains log numbers."""
    writer = make_writer()
    catalogue = make_catalogue()
    print_catalogue(catalogue, list(catalogue.keys()), writer)
    output = writer.getvalue()
    assert "LOG# 0" in output
    assert "LOG# 1" in output
    assert "LOG# 2" in output

  def test_prints_notes_keyword(self):
    """Output contains notes when keyword present."""
    writer = make_writer()
    catalogue = make_catalogue()
    print_catalogue(catalogue, list(catalogue.keys()), writer)
    output = writer.getvalue()
    assert "[straight]" in output
    assert "[bowed]" in output

  def test_no_notes_when_no_keyword(self):
    """Output does not contain notes when no keyword present."""
    writer = make_writer()
    catalogue = make_catalogue()
    print_catalogue(catalogue, [2], writer)
    output = writer.getvalue()
    assert "[" not in output

  def test_sorted_by_thin_end(self):
    """Logs are printed sorted by d_top ascending."""
    writer = make_writer()
    catalogue = make_catalogue()
    print_catalogue(catalogue, list(catalogue.keys()), writer)
    output = writer.getvalue()
    pos0 = output.index("LOG# 0")
    pos1 = output.index("LOG# 1")
    pos2 = output.index("LOG# 2")
    assert pos0 < pos1 < pos2


# ------------------------------------------------------------------
# print_layer
# ------------------------------------------------------------------

class TestPrintLayer:
  """Tests for print_layer function."""

  def test_prints_layer_number(self, make_layer):
    """Output contains layer number."""
    writer = make_writer()
    layer = make_layer()
    state = BuildState(struct_l=33.0)
    state.update_corner_heights(layer)
    print_layer(1, layer, state, writer)
    output = writer.getvalue()
    assert "LAYER #1" in output

  def test_prints_corner_labels(self, make_layer):
    """Output contains all corner labels."""
    writer = make_writer()
    layer = make_layer()
    state = BuildState(struct_l=33.0)
    state.update_corner_heights(layer)
    print_layer(1, layer, state, writer)
    output = writer.getvalue()
    assert "SW:" in output
    assert "NW:" in output
    assert "NE:" in output
    assert "SE:" in output

  def test_prints_log_numbers(self, make_layer):
    """Output contains log numbers."""
    writer = make_writer()
    layer = make_layer()
    state = BuildState(struct_l=33.0)
    state.update_corner_heights(layer)
    print_layer(1, layer, state, writer)
    output = writer.getvalue()
    assert "LOG#" in output

  def test_prints_corner_heights(self, make_layer):
    """Output contains corner heights section."""
    writer = make_writer()
    layer = make_layer()
    state = BuildState(struct_l=33.0)
    state.update_corner_heights(layer)
    print_layer(1, layer, state, writer)
    output = writer.getvalue()
    assert "Corner heights:" in output

  def test_prints_cumulative_heights(self, make_layer):
    """Output contains cumulative heights section."""
    writer = make_writer()
    layer = make_layer()
    state = BuildState(struct_l=33.0)
    state.update_corner_heights(layer)
    print_layer(1, layer, state, writer)
    output = writer.getvalue()
    assert "Cumulative heights:" in output

  def test_prints_logs_remaining(self, make_layer):
    """Output contains logs remaining count."""
    writer = make_writer()
    layer = make_layer()
    state = BuildState(struct_l=33.0)
    state.update_corner_heights(layer)
    print_layer(1, layer, state, writer)
    output = writer.getvalue()
    assert "Logs remaining:" in output


# ------------------------------------------------------------------
# print_summary
# ------------------------------------------------------------------

class TestPrintSummary:
  """Tests for print_summary function."""

  def make_state(self, corner_heights: dict) -> BuildState:
    """Create a BuildState with given corner heights."""
    state = BuildState(struct_l=33.0, target_height=180.0)
    state.corner_heights = corner_heights
    return state

  def test_prints_summary_header(self):
    """Output contains SUMMARY header."""
    writer = make_writer()
    state = self.make_state({SW: 180.0, NW: 179.0, NE: 180.0, SE: 179.0})
    print_summary(state, 180.0, writer)
    output = writer.getvalue()
    assert "SUMMARY" in output

  def test_prints_target_height(self):
    """Output contains target height in feet and inches."""
    writer = make_writer()
    state = self.make_state({SW: 180.0, NW: 179.0, NE: 180.0, SE: 179.0})
    print_summary(state, 180.0, writer)
    output = writer.getvalue()
    assert "Target height:" in output
    assert "15 ft" in output

  def test_prints_actual_height(self):
    """Output contains actual height."""
    writer = make_writer()
    state = self.make_state({SW: 180.0, NW: 179.0, NE: 180.0, SE: 179.0})
    print_summary(state, 180.0, writer)
    output = writer.getvalue()
    assert "Actual height:" in output

  def test_status_ok(self):
    """Status is OK when height and level are within margins."""
    writer = make_writer()
    state = self.make_state({SW: 180.0, NW: 180.0, NE: 180.0, SE: 180.0})
    print_summary(state, 180.0, writer)
    output = writer.getvalue()
    assert "OK" in output

  def test_status_warning_height_exceeded(self):
    """Status warns when height exceeds target by more than 6 inches."""
    writer = make_writer()
    state = self.make_state({SW: 188.0, NW: 188.0, NE: 188.0, SE: 188.0})
    print_summary(state, 180.0, writer)
    output = writer.getvalue()
    assert "WARNING: height exceeded" in output

  def test_status_warning_not_level(self):
    """Status warns when corners are not level."""
    writer = make_writer()
    state = self.make_state({SW: 180.0, NW: 180.0, NE: 180.0, SE: 175.0})
    print_summary(state, 180.0, writer)
    output = writer.getvalue()
    assert "WARNING: not level" in output

  def test_prints_std_dev(self):
    """Output contains standard deviation."""
    writer = make_writer()
    state = self.make_state({SW: 180.0, NW: 179.0, NE: 180.0, SE: 179.0})
    print_summary(state, 180.0, writer)
    output = writer.getvalue()
    assert "Level (std dev):" in output


# ------------------------------------------------------------------
# get_writer
# ------------------------------------------------------------------

class TestGetWriter:
  """Tests for get_writer context manager."""

  def test_returns_stdout_when_no_filename(self):
    """Returns stdout when no filename specified."""
    with get_writer(None) as writer:
      assert writer is sys.stdout

  def test_returns_file_when_filename_given(self, tmp_path):
    """Returns file writer when filename specified."""
    output_file = tmp_path / "test_output.txt"
    with get_writer(str(output_file)) as writer:
      writer.write("test")
    assert output_file.read_text() == "test"
