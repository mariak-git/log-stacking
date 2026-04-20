# Copyright 2015-2026 Maria Mercury <mariak>. All Rights Reserved.
"""Tests for the log catalogue reader and validator."""

import os
import tempfile

import pytest

from loghouse.catalogue import (
  CatalogueEntry,
  LogType,
  read_catalogue,
  get_wall_logs,
  _parse_log_types,
)
from loghouse.models import LogEntry

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def make_csv(rows: list[str],
             header: str = "index,d_top,d_butt,length,notes,log_type") -> str:
  """Write a temporary CSV file and return its path."""
  content = header + "\n" + "\n".join(rows)
  with tempfile.NamedTemporaryFile(
    mode="w", suffix=".csv", delete=False, encoding="utf-8"
  ) as tmp:
    tmp.write(content)
  return tmp.name


# ------------------------------------------------------------------
# LogType parsing
# ------------------------------------------------------------------


class TestParseLogTypes:
  """Tests for _parse_log_types helper."""

  def test_single_wall(self):
    """Parses a single WALL type."""
    assert _parse_log_types("WALL", 0) == {LogType.WALL}

  def test_single_rpsl(self):
    """Parses a single RPSL type."""
    assert _parse_log_types("RPSL", 0) == {LogType.RPSL}

  def test_dual_type(self):
    """Parses dual type WALL|RPSL."""
    assert _parse_log_types("WALL|RPSL", 0) == {LogType.WALL, LogType.RPSL}

  def test_empty_defaults_to_wall(self):
    """Empty string defaults to WALL."""
    assert _parse_log_types("", 0) == {LogType.WALL}

  def test_unrecognized_type_raises(self):
    """Unrecognized type string raises ValueError."""
    with pytest.raises(ValueError, match="unrecognized log type"):
      _parse_log_types("UNKNOWN", 0)

  def test_case_insensitive(self):
    """Type parsing is case insensitive."""
    assert _parse_log_types("wall", 0) == {LogType.WALL}


# ------------------------------------------------------------------
# CatalogueEntry
# ------------------------------------------------------------------


class TestCatalogueEntry:
  """Tests for the CatalogueEntry class."""
  def make_entry(self):
    """Create a default LogEntry for testing."""
    return LogEntry(index=0, d_top=14.0, d_butt=18.0, length=35.0)

  def test_valid_construction(self):
    """A valid CatalogueEntry is created without errors."""
    entry = self.make_entry()
    ce = CatalogueEntry(entry=entry, log_types={LogType.WALL}, notes="straight")
    assert ce.entry == entry
    assert ce.notes == "straight"

  def test_too_many_types_raises(self):
    """More than 4 types raises ValueError."""
    entry = self.make_entry()
    with pytest.raises(ValueError, match="at most 4 types"):
      CatalogueEntry(
        entry=entry, log_types={
          LogType.WALL, LogType.RPSL, LogType.GSL, LogType.CAP, LogType.GIRDER})

  def test_rp_combined_raises(self):
    """RP combined with another type raises ValueError."""
    entry = self.make_entry()
    with pytest.raises(ValueError, match="cannot be combined"):
      CatalogueEntry(entry=entry, log_types={LogType.RP, LogType.WALL})

  def test_cap_combined_raises(self):
    """RP combined with another type raises ValueError."""
    entry = self.make_entry()
    with pytest.raises(ValueError, match="cannot be combined"):
      CatalogueEntry(entry=entry, log_types={LogType.RP, LogType.WALL})

  def test_is_wall_candidate_true(self):
    """WALL only log is a wall candidate."""
    entry = self.make_entry()
    ce = CatalogueEntry(entry=entry, log_types={LogType.WALL})
    assert ce.is_wall_candidate is True

  def test_is_wall_candidate_false_for_rp(self):
    """RP log is not a wall candidate."""
    entry = self.make_entry()
    ce = CatalogueEntry(entry=entry, log_types={LogType.RP})
    assert ce.is_wall_candidate is False

  def test_is_wall_candidate_false_for_dual(self):
    """Dual type WALL|RPSL is not a wall candidate (TODO feature)."""
    entry = self.make_entry()
    ce = CatalogueEntry(entry=entry, log_types={LogType.WALL, LogType.RPSL})
    assert ce.is_wall_candidate is False

  def test_empty_notes(self):
    """Notes defaults to empty string when not provided."""
    entry = self.make_entry()
    ce = CatalogueEntry(entry=entry, log_types={LogType.WALL})
    assert ce.notes == ""


# ------------------------------------------------------------------
# read_catalogue
# ------------------------------------------------------------------


class TestReadCatalogue:
  """Tests for read_catalogue function."""

  def test_reads_valid_csv(self):
    """Reads a valid CSV and returns correct number of entries."""
    path = make_csv([
        "0,14.0,18.0,35.0,straight,WALL",
        "1,14.5,18.5,36.0,,WALL",
    ])
    try:
      catalogue = read_catalogue(path)
      assert len(catalogue) == 2
    finally:
      os.unlink(path)

  def test_correct_dimensions(self):
    """Log dimensions are correctly parsed from CSV."""
    path = make_csv(["0,14.0,18.0,35.0,straight,WALL"])
    try:
      catalogue = read_catalogue(path)
      entry = catalogue[0].entry
      assert entry.d_top == pytest.approx(14.0)
      assert entry.d_butt == pytest.approx(18.0)
      assert entry.length == pytest.approx(35.0)
    finally:
      os.unlink(path)

  def test_notes_parsed(self):
    """Notes field is correctly parsed."""
    path = make_csv(["0,14.0,18.0,35.0,slightly curved,WALL"])
    try:
      catalogue = read_catalogue(path)
      assert catalogue[0].notes == "slightly curved"
    finally:
      os.unlink(path)

  def test_missing_file_raises(self):
    """Missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
      read_catalogue("nonexistent.csv")

  def test_missing_required_column_raises(self):
    """Missing required column raises ValueError."""
    path = make_csv(["0,14.0,18.0"], header="index,d_top,d_butt")
    try:
      with pytest.raises(ValueError, match="Missing required column"):
        read_catalogue(path)
    finally:
      os.unlink(path)

  def test_default_log_type_is_wall(self):
    """Missing log_type column defaults to WALL."""
    path = make_csv(["0,14.0,18.0,35.0,straight"],
                    header="index,d_top,d_butt,length,notes")
    try:
      catalogue = read_catalogue(path)
      assert LogType.WALL in catalogue[0].log_types
    finally:
      os.unlink(path)


# ------------------------------------------------------------------
# get_wall_logs
# ------------------------------------------------------------------


class TestGetWallLogs:
  """Tests for get_wall_logs function."""

  def make_catalogue(self):
    """Create a small catalogue with mixed log types."""
    return {
        0:
            CatalogueEntry(LogEntry(0, 14.0, 18.0, 35.0), {LogType.WALL},
                           "straight"),
        1:
            CatalogueEntry(LogEntry(1, 14.5, 18.5, 36.0), {LogType.RP},
                           "ridge pole"),
        2:
            CatalogueEntry(LogEntry(2, 15.0, 19.0, 35.5),
                           {LogType.WALL, LogType.RPSL}, ""),
        3:
            CatalogueEntry(LogEntry(3, 15.5, 19.5, 36.0), {LogType.CAP}, ""),
    }

  def test_returns_only_wall_logs(self):
    """Only WALL only logs are returned."""
    catalogue = self.make_catalogue()
    wall_logs = get_wall_logs(catalogue)
    assert set(wall_logs.keys()) == {0}

  def test_returns_log_entries(self):
    """Returns LogEntry objects not CatalogueEntry objects."""
    catalogue = self.make_catalogue()
    wall_logs = get_wall_logs(catalogue)
    assert isinstance(wall_logs[0], LogEntry)

  def test_empty_catalogue(self):
    """Empty catalogue returns empty dict."""
    assert get_wall_logs({}) == {}
