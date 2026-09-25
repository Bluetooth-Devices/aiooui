"""Async OUI (MAC vendor prefix) lookups."""

from __future__ import annotations

__version__ = "0.1.9"

import asyncio
import pathlib

_NL = b"\n"
_KEY_LEN = 6

_OUI_DATA_FILE = pathlib.Path(__file__).parent.joinpath("oui.data")


class OUIManager:
    """OUI data manager."""

    def __init__(self) -> None:
        self._oui_to_vendor: bytes = b""
        self._load_future: asyncio.Future[None] | None = None

    def get_vendor(self, mac: str) -> str | None:
        """Return the vendor name for *mac*, or ``None``."""
        if not self._oui_to_vendor:
            raise RuntimeError("OUI data not loaded, call async_load first")
        key = mac.replace(":", "")[:_KEY_LEN].upper().encode()
        return _bisect(self._oui_to_vendor, key)

    async def async_load(self) -> None:
        """Load OUI data from disk (idempotent)."""
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

    def _load_oui_data(self) -> bytes:
        """Read oui.data into bytes."""
        return _OUI_DATA_FILE.read_bytes()


def _bisect(data: bytes, key: bytes) -> str | None:
    """Binary-search sorted OUI=VENDOR lines for key."""
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
    """Return whether OUI data has been loaded."""
    return bool(_OUI_MANAGER._oui_to_vendor)


def get_vendor(mac: str) -> str | None:
    """Return the vendor name for *mac*, or ``None``."""
    return _OUI_MANAGER.get_vendor(mac)


async def async_load() -> None:
    """Load OUI data from disk (idempotent)."""
    await _OUI_MANAGER.async_load()


__all__ = ["async_load", "get_vendor", "is_loaded"]
