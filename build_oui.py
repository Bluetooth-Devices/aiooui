"""Build oui table."""

from __future__ import annotations

import asyncio
import os
import pathlib
import struct
import time
from typing import Any

import setuptools

_OUI_URL = "https://standards-oui.ieee.org/oui.txt"
# The IEEE site answers HTTP 418 to the default python-requests and aiohttp
# user agents, so identify the project instead.
_HEADERS = {"User-Agent": "aiooui (+https://github.com/Bluetooth-Devices/aiooui)"}
# The 6.6 MB list can take close to a minute to arrive from the IEEE site.
_TIMEOUT = 180


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
        except ValueError:
            # Malformed IEEE data is deterministic: fail at once instead of retrying and
            # silently keeping the existing file.
            raise
        except Exception as e:
            # The IEEE site is slow and drops connections under load, so back
            # off between attempts: 5, 10, 20, 40, 80 and 160 seconds.
            time.sleep(5 * 2**attempt)
            print(f"Failed to regenerate OUI data: {e}")

    if os.environ.get("AIOOUI_REQUIRE_REGENERATE"):
        raise RuntimeError("Failed to regenerate OUI data")

    print("Using existing data.")


def _regenerate_ouis_requests() -> None:
    import requests

    resp = requests.get(_OUI_URL, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    _update_from_oui_content(resp.content)


async def _regenerate_ouis_aiohttp() -> None:
    import aiohttp

    timeout = aiohttp.ClientTimeout(total=_TIMEOUT)
    async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
        async with session.get(_OUI_URL) as resp:
            resp.raise_for_status()
            _update_from_oui_content(await resp.read())


def _update_from_oui_content(oui_bytes: bytes) -> None:
    oui_to_vendor: dict[int, bytes] = {}
    for line in oui_bytes.splitlines():
        if b"(base 16)" in line:
            oui, _, vendor = line.partition(b"(base 16)")
            oui = oui.strip().upper()
            if len(oui) != 6 or oui.strip(b"0123456789ABCDEF"):
                raise ValueError(f"Unexpected OUI {oui!r}")
            oui_to_vendor[int(oui, 16)] = vendor.strip()
    file = pathlib.Path(__file__)
    target_file = file.parent.joinpath("src").joinpath("aiooui").joinpath("oui.data")
    target_file.write_bytes(_pack(oui_to_vendor))


def _pack(oui_to_vendor: dict[int, bytes]) -> bytes:
    """
    Serialize the table in the layout aiooui/__init__.py searches.

    All integers are little-endian uint32:
      magic  b"OUI1"
      count  number of entries, n
      keys   n * uint32, the OUI as a 24-bit integer, sorted ascending, unique
      offs   n * uint32, byte offset of the entry's vendor name inside the blob
      blob   utf-8 vendor names, each newline terminated, deduplicated

    Sorted keys are what make the binary search work, so they are produced here
    and checked again by tests/test_init.py::test_data_file_is_valid.
    """
    blob = bytearray()
    blob_offsets: dict[bytes, int] = {}
    keys: list[int] = []
    offsets: list[int] = []
    for key in sorted(oui_to_vendor):
        vendor = oui_to_vendor[key]
        if b"\n" in vendor or not vendor:
            raise ValueError(f"Unexpected vendor {vendor!r} for OUI {key:06X}")
        vendor.decode()
        if vendor not in blob_offsets:
            blob_offsets[vendor] = len(blob)
            blob += vendor + b"\n"
        keys.append(key)
        offsets.append(blob_offsets[vendor])
    count = len(keys)
    return b"".join(
        (
            struct.pack("<4sI", b"OUI1", count),
            struct.pack(f"<{count}I", *keys),
            struct.pack(f"<{count}I", *offsets),
            blob,
        )
    )


if __name__ == "__main__":
    build({})
