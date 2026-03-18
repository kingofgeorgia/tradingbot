from __future__ import annotations

import csv
from pathlib import Path


class CsvJournal:
    def __init__(self, file_path: Path, fieldnames: list[str]) -> None:
        self._file_path = file_path
        self._fieldnames = fieldnames
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            with self._file_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self._fieldnames)
                writer.writeheader()

    def write(self, row: dict[str, object]) -> None:
        with self._file_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._fieldnames)
            writer.writerow(row)
