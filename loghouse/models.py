# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.

"""Core domain models for the log house stacking algorithm.

Contains two main classes:
    LogEntry: A raw catalogue entry representing an unplaced log.
    Log: A placed log with computed dimensions based on wall orientation.
    Layer: A course of 4 logs forming one level of the wall.
"""

import logging
from dataclasses import dataclass
from loghouse.config import THIN_END, FAT_END, PASS_END_LABELS, CORNERS, ORIENT

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """A raw log entry from the catalogue.

    Attributes:
        index: Unique identifier from the catalogue.
        d_top: Diameter at the narrow (top) end in inches.
        d_butt: Diameter at the wide (butt) end in inches.
        length: Length of the log in feet.
    """
    index: int
    d_top: float
    d_butt: float
    length: float

    def __post_init__(self) -> None:
        """Validate log dimensions on construction."""
        if self.length <= 0:
            raise ValueError(f"Log #{self.index}: length must be positive, got {self.length}")
        if self.d_top < 0 or self.d_butt < 0:
            raise ValueError(f"Log #{self.index}: diameters must be non-negative")
        if self.d_butt < self.d_top:
            raise ValueError(f"Log #{self.index}: d_butt must be >= d_top")

    @property
    def taper(self) -> float:
        """Taper rate in inches per foot."""
        return (self.d_butt - self.d_top) / self.length
    

class Log:
    """A placed log with computed dimensions based on wall orientation.

    A Log is created from a LogEntry when it is assigned to a specific
    wall in a layer. The overdangle and adjusted end diameters are
    computed at construction time.

    Attributes:
        entry: The original LogEntry from the catalogue.
        index: Unique identifier, copied from entry for convenience.
        pass_end: Which end (THIN_END or FAT_END) is the pass end.
        pass_str: Human readable pass end label.
        struct_l: The wall length this log is placed against.
        overdangle: How much the log extends past struct_l.
        top_new: Adjusted top diameter after overdangle calculation.
        butt_new: Adjusted butt diameter after overdangle calculation.
    """

    def __init__(self, entry: LogEntry, pass_end: int, struct_l: float) -> None:
        """Place a log on a wall.

        Args:
            entry: The catalogue entry for this log.
            pass_end: THIN_END or FAT_END indicating orientation.
            struct_l: The wall length in feet.

        Raises:
            ValueError: If log is shorter than struct_l.
        """
        if entry.length < struct_l:
            raise ValueError(
                f"Log #{entry.index} length {entry.length:.2f} is shorter "
                f"than struct_l {struct_l:.2f}"
            )

        self.entry = entry
        self.index = entry.index
        self.pass_end = pass_end
        self.pass_str = PASS_END_LABELS[pass_end]
        self.struct_l = struct_l

        self.overdangle = entry.length - struct_l
        self.top_new = entry.d_top
        self.butt_new = entry.d_butt

        self._compute_adjusted_ends()

    def _compute_adjusted_ends(self) -> None:
        """Adjust end diameters based on overdangle and pass end."""
        if self.pass_end == FAT_END:
            # Butt end is the pass end — trim butt diameter by overdangle
            self.butt_new = self.entry.d_butt - self.overdangle * self.entry.taper
        else:
            # Thin end is the pass end — adjust top diameter upward
            self.top_new = self.entry.d_top + self.overdangle * self.entry.taper

    def get_corner_diameter(self) -> float:
        """Get the diameter at the corner connection point.

        Returns the adjusted diameter at the pass end — the diameter
        of this log at exactly struct_l from its start.

        Returns:
            The adjusted diameter at the corner.
        """
        return self.butt_new if self.pass_end == FAT_END else self.top_new

    def __repr__(self) -> str:
        return (
            f"Log(index={self.index}, pass={self.pass_str}, "
            f"top={self.entry.d_top:.2f}, butt={self.entry.d_butt:.2f}, "
            f"top_new={self.top_new:.2f}, butt_new={self.butt_new:.2f}, "
            f"overdangle={self.overdangle:.2f})"
        )    