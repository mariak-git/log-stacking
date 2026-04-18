# Copyright 2015 Maria Mercury <mariak>. All Rights Reserved.
"""Catalogue module for reading and validating the log catalogue from CSV file.

Typical usage example:

  catalogue = read_catalogue('data/sample_catalogue.csv')
"""

import csv
import logging
from enum import Enum
from typing import Optional

from loghouse.models import LogEntry

logger = logging.getLogger(__name__)


class LogType(Enum):
  """Type/role of a log in the structure.

  A log can have at most two types. At this stage the program
  only processes WALL logs for stacking.

  # TODO(mariak): Add logic to pick and validate non-wall logs
  # (GSL, GIRDER, CAP, RPSL, RP) from catalogue before stacking.
  # TODO(mariak): Add program-assisted validation of user's type
  # assignments based on log dimensions.
  """
  WALL = "WALL"
  RPSL = "RPSL"  # Ridge Pole Support Log — 3 required
  GSL = "GSL"  # Girder Support Log — 1 required
  GIRDER = "GIRDER"  # 2nd floor support log — 1 required
  CAP = "CAP"  # Top layer log — 2 required, ~20% longer than WALL
  RP = "RP"  # Ridge Pole — 1 required, largest/longest, never stacked


# Log types that are never used for wall stacking
_NON_WALL_TYPES = {LogType.RP, LogType.CAP}


class CatalogueEntry:
  """A full catalogue entry including stacking data and metadata.

  Attributes:
    entry: The LogEntry with core dimensions for stacking.
    log_types: Set of assigned LogType values (at most 2).
    notes: Optional free text description of the log.
  """

  def __init__(self,
               entry: LogEntry,
               log_types: set,
               notes: Optional[str] = None) -> None:
    """Initialize a CatalogueEntry.

    Args:
      entry: The core LogEntry with dimensions.
      log_types: Set of LogType values assigned to this log.
      notes: Optional description string.

    Raises:
      ValueError: If more than 2 types are assigned.
      ValueError: If RP or CAP is combined with any other type.
    """
    if len(log_types) > 2:
      raise ValueError(
          f"Log #{entry.index}: at most 2 types allowed, got {log_types}")
    for t in _NON_WALL_TYPES:
      if t in log_types and len(log_types) > 1:
        raise ValueError(
            f"Log #{entry.index}: {t.value} cannot be combined with other types"
        )
    self.entry = entry
    self.log_types = log_types
    self.notes = notes or ""

  @property
  def is_wall_candidate(self) -> bool:
    """True if this log is eligible for wall stacking.

    # TODO(mariak): extend to include WALL|RPSL, WALL|GSL, WALL|GIRDER
    # dual type logs once non-wall log selection logic is implemented.
    """
    return self.log_types == {LogType.WALL}

  def __repr__(self) -> str:
    return (f"CatalogueEntry(index={self.entry.index}, "
            f"types={[t.value for t in self.log_types]}, "
            f"notes='{self.notes}')")


def _parse_log_types(raw: str, index: int) -> set:
  """Parse a log type string into a set of LogType values.

  Args:
    raw: Raw string from CSV e.g. 'WALL' or 'WALL|RPSL'.
    index: Log index for error messages.

  Returns:
    Set of LogType values.

  Raises:
    ValueError: If an unrecognized type string is encountered.
  """
  if not raw or not raw.strip():
    return {LogType.WALL}
  parts = [p.strip().upper() for p in raw.split("|")]
  result = set()
  for part in parts:
    try:
      result.add(LogType(part))
    except ValueError as exc:
      raise ValueError(
        f"Log #{index}: unrecognized log type '{part}'"
      ) from exc
  return result


def read_catalogue(filepath: str) -> dict[int, CatalogueEntry]:
  """Read and validate a log catalogue from a CSV file.

  Expected CSV columns:
    index, d_top, d_butt, length, notes (optional), log_type (optional)

  Args:
    filepath: Path to the CSV file.

  Returns:
    Dict mapping log index to CatalogueEntry.

  Raises:
    FileNotFoundError: If the CSV file does not exist.
    ValueError: If any row has invalid or missing required fields.
  """
  catalogue = {}
  with open(filepath, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
      try:
        index = int(row["index"])
        d_top = float(row["d_top"])
        d_butt = float(row["d_butt"])
        length = float(row["length"])
        notes = row.get("notes", "").strip()
        log_type_raw = row.get("log_type", "WALL")
        log_types = _parse_log_types(log_type_raw, index)
        entry = LogEntry(
            index=index,
            d_top=d_top,
            d_butt=d_butt,
            length=length,
        )
        catalogue[index] = CatalogueEntry(
            entry=entry,
            log_types=log_types,
            notes=notes,
        )
        logger.debug("Loaded log #%d: %s", index, catalogue[index])
      except KeyError as e:
        raise ValueError(f"Missing required column: {e}") from e
  logger.info("Loaded %d logs from catalogue", len(catalogue))
  return catalogue


def get_wall_logs(catalogue: dict[int, CatalogueEntry]) -> dict[int, LogEntry]:
  """Extract only WALL candidate logs from the catalogue.

  Args:
    catalogue: Full catalogue as returned by read_catalogue.

  Returns:
    Dict mapping index to LogEntry for WALL logs only.
  """
  # TODO(mariak): extend to include dual type logs (WALL|RPSL etc.)
  # once non-wall log selection logic is implemented.
  return {
      index: ce.entry for index, ce in catalogue.items() if ce.is_wall_candidate
  }
