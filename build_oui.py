"""Build oui table."""

from __future__ import annotations

from typing import Any

from generate_oui_data import generate


def build(setup_kwargs: dict[str, Any]) -> None:
    """Build the OUI data."""
    generate()
