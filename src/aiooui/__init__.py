"""Async OUI (MAC vendor prefix) lookups."""

from __future__ import annotations

__version__ = "0.1.11"

import asyncio
import mmap
import pathlib
import struct
import sys
from bisect import bisect_left
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

_NL = b"\n"
_KEY_LEN = 6

# oui.data layout, written by build_oui.py (all integers little-endian uint32):
#   magic  b"OUI1"
#   count  number of entries, n
#   keys   n * uint32, the OUI as a 24-bit integer, sorted ascending, unique
#   offs   n * uint32, byte offset of the entry's vendor name inside the blob
#   blob   utf-8 vendor names, each terminated by b"\n", deduplicated
_MAGIC = b"OUI1"
_HEADER = struct.Struct("<4sI")
_U32 = 4

_OUI_DATA_FILE = pathlib.Path(__file__).parent.joinpath("oui.data")


class OUIManager:
    """OUI data manager."""

    def __init__(self) -> None:
        self._data: bytes | mmap.mmap = b""
        self._keys: Sequence[int] | None = None
        self._offsets: Sequence[int] = ()
        self._count = 0
        self._blob_start = 0
        self._load_future: asyncio.Future[None] | None = None

    def get_vendor(self, mac: str) -> str | None:
        """Return the vendor name for *mac*, or ``None``."""
        keys = self._keys
        if keys is None:
            raise RuntimeError("OUI data not loaded, call async_load first")
        prefix = mac.replace(":", "")[:_KEY_LEN]
        if len(prefix) != _KEY_LEN:
            return None
        try:
            key = int(prefix, 16)
        except ValueError:
            return None
        i = bisect_left(keys, key)
        if i < self._count and keys[i] == key:
            data = self._data
            start = self._blob_start + self._offsets[i]
            return data[start : data.find(_NL, start)].decode()
        return None

    async def async_load(self) -> None:
        """Load OUI data from disk (idempotent)."""
        if self._keys is not None:
            return
        if self._load_future:
            await self._load_future
            return
        loop = asyncio.get_running_loop()
        self._load_future = loop.create_future()
        try:
            data = await loop.run_in_executor(None, self._load_oui_data)
            self._attach(data)
        except Exception as err:
            self._load_future.set_exception(err)
            raise
        else:
            self._load_future.set_result(None)
        finally:
            self._load_future = None

    def _load_oui_data(self) -> bytes | mmap.mmap:
        """Memory-map oui.data read-only, falling back to bytes if mmap fails."""
        with _OUI_DATA_FILE.open("rb") as f:
            try:
                data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            except (OSError, ValueError):
                return f.read()
        for offset in range(0, len(data), mmap.PAGESIZE):
            data[offset]
        return data

    def _attach(self, data: bytes | mmap.mmap) -> None:
        """Validate the table header and expose the key and offset arrays."""
        magic, count = _HEADER.unpack_from(data)
        keys_start = _HEADER.size
        offsets_start = keys_start + count * _U32
        blob_start = offsets_start + count * _U32
        if magic != _MAGIC or len(data) < blob_start:
            raise RuntimeError(f"{_OUI_DATA_FILE} is not a valid OUI table")
        self._data = data
        self._keys = _u32_view(data, keys_start, count)
        self._offsets = _u32_view(data, offsets_start, count)
        self._count = count
        self._blob_start = blob_start


def _u32_view(data: bytes | mmap.mmap, start: int, count: int) -> Sequence[int]:
    """A sequence of *count* little-endian uint32 values starting at *start*."""
    view = memoryview(data)[start : start + count * _U32]
    if sys.byteorder == "little":
        return view.cast("I")
    return struct.unpack(f"<{count}I", view)


_OUI_MANAGER = OUIManager()


def is_loaded() -> bool:
    """Return whether OUI data has been loaded."""
    return _OUI_MANAGER._keys is not None


def get_vendor(mac: str) -> str | None:
    """Return the vendor name for *mac*, or ``None``."""
    return _OUI_MANAGER.get_vendor(mac)


async def async_load() -> None:
    """Load OUI data from disk (idempotent)."""
    await _OUI_MANAGER.async_load()


__all__ = ["async_load", "get_vendor", "is_loaded"]
