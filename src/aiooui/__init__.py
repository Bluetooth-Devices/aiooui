"""
Async OUI (MAC vendor prefix) lookups.

How lookups work: ``oui.data`` is never expanded into a dict. ``async_load`` maps
the file read-only (in the executor), and ``get_vendor`` binary-searches the
mapping, so the process holds ~0 private memory for the table. The pages are
touched once during ``async_load`` (so lookups never wait on disk) and stay as
clean page cache the kernel can reclaim. If mmap is unavailable, the file is read
into ``bytes`` instead.

The binary search requires ``oui.data`` to be one ``OUI=VENDOR`` entry per line,
with OUI = exactly 6 uppercase hex digits, unique, and the file SORTED by OUI.
``build_oui.py`` writes it that way and ``tests/test_init.py`` checks it; do not
edit the file by hand.
"""

from __future__ import annotations

__version__ = "0.1.9"

import asyncio
import mmap
import pathlib

_NL = b"\n"
_KEY_LEN = 6  # "001122"; oui.data is "OUI=VENDOR" lines, sorted by OUI (build_oui.py)

_OUI_DATA_FILE = pathlib.Path(__file__).parent.joinpath("oui.data")


class OUIManager:
    """Manages the OUI data."""

    def __init__(self) -> None:
        """Initialize the OUIManager."""
        self._oui_to_vendor: bytes | mmap.mmap = b""
        self._load_future: asyncio.Future[None] | None = None

    def get_vendor(self, mac: str) -> str | None:
        """Get the vendor for a MAC address."""
        if not self._oui_to_vendor:
            raise RuntimeError("OUI data not loaded, call async_load first")
        key = mac.replace(":", "")[:_KEY_LEN].upper().encode()
        return _bisect(self._oui_to_vendor, key)

    async def async_load(self) -> None:
        """Load the OUI data."""
        if self._oui_to_vendor:
            return
        if self._load_future:
            await self._load_future
            return
        loop = asyncio.get_running_loop()
        self._load_future = loop.create_future()
        try:
            self._oui_to_vendor = await loop.run_in_executor(None, self._load_oui_data)
        except Exception as err:
            self._load_future.set_exception(err)
            raise
        else:
            self._load_future.set_result(None)
        finally:
            self._load_future = None

    def _load_oui_data(self) -> bytes | mmap.mmap:
        """
        Load the OUI data.

        The file is memory-mapped read-only and binary-searched on lookup instead of
        being expanded into a dict of ~37k str entries (~5.6 MB). The pages are
        faulted in here, in the executor, so that lookups on the event loop do not
        wait on disk reads; they are clean page cache the kernel can reclaim. Falls
        back to reading the file into bytes (~1.1 MB) if mmap fails.
        """
        with _OUI_DATA_FILE.open("rb") as f:
            try:
                data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            except (OSError, ValueError):
                return f.read()
        for offset in range(0, len(data), mmap.PAGESIZE):
            data[offset]  # touch every page once (warms page cache and page table)
        return data


def _bisect(data: bytes | mmap.mmap, key: bytes) -> str | None:
    """Binary search the sorted "OUI=VENDOR" lines in data for key."""
    lo, hi = 0, len(data)
    while lo < hi:
        start = data.rfind(_NL, 0, (lo + hi) // 2) + 1
        end = data.find(_NL, start)
        if end < 0:
            end = len(data)
        line_key = data[start : start + _KEY_LEN]
        if line_key == key:
            vendor = data[start + _KEY_LEN + 1 : end].rstrip(b"\r")
            return vendor.decode("utf-8", "replace")
        if line_key < key:
            lo = end + 1
        else:
            hi = start
    return None


_OUI_MANAGER = OUIManager()


def is_loaded() -> bool:
    """Return if the OUI data is loaded."""
    return bool(_OUI_MANAGER._oui_to_vendor)


def get_vendor(mac: str) -> str | None:
    """Get the vendor for a MAC address."""
    return _OUI_MANAGER.get_vendor(mac)


async def async_load() -> None:
    """Load the OUI data."""
    await _OUI_MANAGER.async_load()


__all__ = ["async_load", "get_vendor", "is_loaded"]
