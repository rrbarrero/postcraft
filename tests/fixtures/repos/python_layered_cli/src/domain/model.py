"""Domain entities."""

from dataclasses import dataclass


@dataclass
class Report:
    title: str
    body: str
