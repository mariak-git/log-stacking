# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.
"""
Constants defining structural parameters and orientation enumerations
for the log house stacking algorithm.
"""

# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

# Structure defaults and minimums
DEFAULT_STRUCT_L: float = 33.0   # feet
DEFAULT_STRUCT_H: float = 15.0   # feet
MIN_STRUCT_L: float = 14.0       # feet
MIN_STRUCT_H_FT: float = 1.0     # feet

# ---------------------------------------------------------------------------
# Log end types
# ---------------------------------------------------------------------------

THIN_END: int = 0
FAT_END: int = 1

PASS_END_LABELS: dict[int, str] = {
    THIN_END: "THIN_END",
    FAT_END: "FAT_END",
}

# ---------------------------------------------------------------------------
# Corners (order matters — used as index into a 4-log layer stack)
# ---------------------------------------------------------------------------

SW: int = 0
NW: int = 1
NE: int = 2
SE: int = 3

CORNERS: dict[int, str] = {
    SW: "SW",
    NW: "NW",
    NE: "NE",
    SE: "SE",
}

# ---------------------------------------------------------------------------
# Cardinal directions (walls)
# ---------------------------------------------------------------------------

NORTH: int = 2
WEST: int = 4
EAST: int = 8
SOUTH: int = 16

ORIENT: dict[int, str] = {
    NORTH: "NORTH",
    WEST: "WEST",
    EAST: "EAST",
    SOUTH: "SOUTH",
}
