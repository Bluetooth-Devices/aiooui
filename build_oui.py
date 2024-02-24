"""Build oui table."""

from __future__ import annotations

import os
import pathlib
from typing import Any

import setuptools


def build(setup_kwargs: dict[str, Any]) -> None:
    """Build the OUI data."""
    setup_kwargs["maintainer"] = "Bluetooth Devices"
    setup_kwargs["maintainer_email"] = "bluetooth@koston.org"
    setuptools.setup(
        **setup_kwargs,
        long_description_content_type="text/markdown",
        script_args=["bdist_wheel"],
        options={
            "bdist_wheel": {"plat_name": "any"},
        },
    )

    for _ in range(3):
        try:
            _regenerate_ouis()
            return
        except Exception as e:
            print(f"Failed to regenerate OUI data: {e}")

    if os.environ.get("AIOOUI_REQUIRE_REGENERATE"):
        raise RuntimeError("Failed to regenerate OUI data")

    print("Using existing data.")


def _regenerate_ouis() -> None:
    import requests  # type: ignore

    resp = requests.get("https://standards-oui.ieee.org/oui.txt", timeout=20)
    resp.raise_for_status()
    oui_bytes = resp.content
    oui_to_vendor = {}
    for line in oui_bytes.splitlines():
        if b"(base 16)" in line:
            oui, _, vendor = line.partition(b"(base 16)")
            oui_to_vendor[oui.strip()] = vendor.strip()
    file = pathlib.Path(__file__)
    target_file = file.parent.joinpath("src").joinpath("aiooui").joinpath("oui.data")
    with open(target_file, "wb") as f:
        f.write(b"\n".join(b"=".join((o, v)) for o, v in oui_to_vendor.items()))


if __name__ == "__main__":
    build({})
