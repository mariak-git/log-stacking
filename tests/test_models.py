# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Tests for the Log and Layer models in loghouse.models."""

import pytest
from loghouse.models import LogEntry, Log
from loghouse.config import THIN_END, FAT_END


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