# Copyright 2015-2026 Maria Mercury <mariak>. All Rights Reserved.
"""Tests for the command line interface in loghouse.cli."""

import argparse
import os

import pytest

from loghouse.cli import _parse_args, _validate_args, main
from loghouse.config import DEFAULT_STRUCT_H, DEFAULT_STRUCT_L

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_csv(tmp_path, rows: list[str]) -> str:
  """Write a temporary catalogue CSV and return its path."""
  header = "index,d_top,d_butt,length,notes,log_type"
  content = header + "\n" + "\n".join(rows)
  path = tmp_path / "catalogue.csv"
  path.write_text(content, encoding="utf-8")
  return str(path)


def make_valid_catalogue(tmp_path, count: int = 52) -> str:
  """Create a valid catalogue CSV with enough logs for stacking."""
  rows = []
  for i in range(count):
    d_top = round(14.0 + i * 0.1, 2)
    d_butt = round(d_top + 4.0, 2)
    rows.append(f"{i},{d_top},{d_butt},35.0,,WALL")
  return make_csv(tmp_path, rows)


# ------------------------------------------------------------------
# _parse_args
# ------------------------------------------------------------------

class TestParseArgs:
  """Tests for _parse_args function."""
  def test_required_logfile(self):
    """--logfile is required."""
    with pytest.raises(SystemExit):
      _parse_args(["--length", "33"])

  def test_default_length(self, tmp_path):
    """Default length is DEFAULT_STRUCT_L."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path])
    assert args.length == DEFAULT_STRUCT_L

  def test_default_height(self, tmp_path):
    """Default height is DEFAULT_STRUCT_H."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path])
    assert args.height == DEFAULT_STRUCT_H

  def test_default_level_margin(self, tmp_path):
    """Default level margin is 1.5."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path])
    assert args.level_margin == 1.5

  def test_default_taper_margin(self, tmp_path):
    """Default taper margin is 0.01."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path])
    assert args.taper_margin == 0.01

  def test_default_no_catalogue_false(self, tmp_path):
    """Default no_catalogue is False."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path])
    assert args.no_catalogue is False

  def test_default_verbose_false(self, tmp_path):
    """Default verbose is False."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path])
    assert args.verbose is False

  def test_custom_length(self, tmp_path):
    """Custom length is parsed correctly."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path, "--length", "35.0"])
    assert args.length == 35.0

  def test_custom_height(self, tmp_path):
    """Custom height is parsed correctly."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path, "--height", "12.0"])
    assert args.height == 12.0

  def test_no_catalogue_flag(self, tmp_path):
    """--no-catalogue flag is parsed correctly."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path, "--no-catalogue"])
    assert args.no_catalogue is True

  def test_verbose_flag(self, tmp_path):
    """--verbose flag is parsed correctly."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path, "--verbose"])
    assert args.verbose is True

  def test_output_flag(self, tmp_path):
    """--output flag is parsed correctly."""
    path = make_valid_catalogue(tmp_path)
    args = _parse_args(["--logfile", path, "--output", "out.txt"])
    assert args.output == "out.txt"


# ------------------------------------------------------------------
# _validate_args
# ------------------------------------------------------------------

class TestValidateArgs:
  """Tests for _validate_args function."""

  def make_args(self, tmp_path, **kwargs):
    """Create a valid args namespace with optional overrides."""
    path = make_valid_catalogue(tmp_path)
    defaults = {
      "length": 33.0,
      "logfile": path,
      "height": 15.0,
      "level_margin": 1.5,
      "taper_margin": 0.01,
      "output": None,
      "no_catalogue": False,
      "verbose": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)

  def test_valid_args_pass(self, tmp_path):
    """Valid args pass validation without error."""
    args = self.make_args(tmp_path)
    _validate_args(args)  # should not raise

  def test_length_too_small_exits(self, tmp_path):
    """Length below minimum causes SystemExit."""
    args = self.make_args(tmp_path, length=5.0)
    with pytest.raises(SystemExit):
      _validate_args(args)

  def test_height_too_small_exits(self, tmp_path):
    """Height below minimum causes SystemExit."""
    args = self.make_args(tmp_path, height=0.5)
    with pytest.raises(SystemExit):
      _validate_args(args)

  def test_level_margin_zero_exits(self, tmp_path):
    """Zero level margin causes SystemExit."""
    args = self.make_args(tmp_path, level_margin=0.0)
    with pytest.raises(SystemExit):
      _validate_args(args)

  def test_taper_margin_zero_exits(self, tmp_path):
    """Zero taper margin causes SystemExit."""
    args = self.make_args(tmp_path, taper_margin=0.0)
    with pytest.raises(SystemExit):
      _validate_args(args)


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------

class TestMain:
  """Tests for main function."""

  def test_missing_logfile_exits(self):
    """Missing --logfile causes SystemExit."""
    with pytest.raises(SystemExit):
      main(["--length", "33"])

  def test_nonexistent_logfile_exits(self):
    """Nonexistent logfile causes SystemExit."""
    with pytest.raises(SystemExit):
      main(["--logfile", "nonexistent.csv"])

  def test_runs_successfully(self, tmp_path):
    """main runs successfully with valid catalogue."""
    path = make_valid_catalogue(tmp_path)
    main([
      "--logfile", path,
      "--length", "33",
      "--height", "2.0",
      "--no-catalogue",
    ])

  def test_output_to_file(self, tmp_path):
    """main writes output to file when --output specified."""
    path = make_valid_catalogue(tmp_path)
    output_file = str(tmp_path / "output.txt")
    main([
      "--logfile", path,
      "--length", "33",
      "--height", "2.0",
      "--no-catalogue",
      "--output", output_file,
    ])
    assert os.path.exists(output_file)
    with open(output_file, encoding="utf-8") as f:
      content = f.read()
    assert "LAYER" in content
    assert "SUMMARY" in content

  def test_catalogue_printed_by_default(self, tmp_path, capsys):
    """Catalogue is printed by default."""
    path = make_valid_catalogue(tmp_path)
    main([
      "--logfile", path,
      "--length", "33",
      "--height", "2.0",
    ])
    captured = capsys.readouterr()
    assert "WALL LOGS CATALOGUE" in captured.out

  def test_no_catalogue_flag(self, tmp_path, capsys):
    """Catalogue is not printed when --no-catalogue specified."""
    path = make_valid_catalogue(tmp_path)
    main([
      "--logfile", path,
      "--length", "33",
      "--height", "2.0",
      "--no-catalogue",
    ])
    captured = capsys.readouterr()
    assert "WALL LOGS CATALOGUE" not in captured.out

  def test_summary_always_printed(self, tmp_path, capsys):
    """Summary is always printed at the end."""
    path = make_valid_catalogue(tmp_path)
    main([
      "--logfile", path,
      "--length", "33",
      "--height", "2.0",
      "--no-catalogue",
    ])
    captured = capsys.readouterr()
    assert "SUMMARY" in captured.out
