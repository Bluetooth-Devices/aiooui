"""Build oui table."""

from __future__ import annotations

import asyncio
import os
import pathlib
import time
from typing import Any

import setuptools


def build(setup_kwargs: dict[str, Any]) -> None:
    """Build the OUI data."""
    setup_kwargs["maintainer"] = "Bluetooth Devices"
    setup_kwargs["maintainer_email"] = "bluetooth@koston.org"
    setup_kwargs["license"] = "MIT"
    setuptools.setup(
        **setup_kwargs,
        long_description_content_type="text/markdown",
        script_args=["bdist_wheel"],
        options={
            "bdist_wheel": {"plat_name": "any"},
        },
    )
    if os.environ.get("AIOOUI_SKIP_REGENERATE"):
        print("Skipping OUI data regeneration.")
        return

    for attempt in range(6):
        try:
            if attempt % 2 == 0:
                asyncio.run(_regenerate_ouis_aiohttp())
            else:
                _regenerate_ouis_requests()
            print(f"Regenerated OUI data on attempt {attempt + 1}.")
            return
        except Exception as e:
            time.sleep(5)
            print(f"Failed to regenerate OUI data: {e}")

    if os.environ.get("AIOOUI_REQUIRE_REGENERATE"):
        raise RuntimeError("Failed to regenerate OUI data")

    print("Using existing data.")


def _regenerate_ouis_requests() -> None:
    import requests  # type: ignore

    resp = requests.get("https://standards-oui.ieee.org/oui.txt", timeout=20)
    resp.raise_for_status()
    _update_from_oui_content(resp.content)


async def _regenerate_ouis_aiohttp() -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get("https://standards-oui.ieee.org/oui.txt") as resp:
            resp.raise_for_status()
            _update_from_oui_content(await resp.read())


def _update_from_oui_content(oui_bytes: bytes) -> None:
    oui_to_vendor = {}
    for line in oui_bytes.splitlines():
        if b"(base 16)" in line:
            oui, _, vendor = line.partition(b"(base 16)")
            oui_to_vendor[oui.strip()] = vendor.strip()
    file = pathlib.Path(__file__)
    target_file = file.parent.joinpath("src").joinpath("aiooui").joinpath("oui.data")
    with open(target_file, "wb") as f:
        f.write(b"\n".join(b"=".join((o, v)) for o, v in sorted(oui_to_vendor.items())))


if __name__ == "__main__":
    build({})
