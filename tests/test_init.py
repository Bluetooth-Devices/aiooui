import mmap
import pathlib
import random
import struct
import sys
import types

import pytest

import aiooui
from aiooui import async_load, get_vendor, is_loaded

_DATA_FILE = pathlib.Path(aiooui.__file__).parent.joinpath("oui.data")


@pytest.mark.asyncio
async def test_get_without_load() -> None:
    """Test getting a vendor without loading."""
    assert is_loaded() is False
    with pytest.raises(RuntimeError):
        get_vendor("00:00:00:00:00:00")


@pytest.mark.asyncio
async def test_get_vendor() -> None:
    """Test getting a vendor."""
    assert is_loaded() is False
    await async_load()
    assert is_loaded() is True
    await async_load()
    assert is_loaded() is True
    assert get_vendor("00:00:00:00:00:00") == "XEROX CORPORATION"


@pytest.mark.asyncio
async def test_matches_full_table() -> None:
    """Every OUI in the data file resolves to the vendor the reference decoder gives."""
    await async_load()
    table = _reference_table()
    for oui, vendor in table.items():
        mac = ":".join((oui[0:2], oui[2:4], oui[4:6], "11", "22", "33"))
        assert get_vendor(mac) == vendor
        assert get_vendor(mac.lower()) == vendor
    assert get_vendor("FF:FF:FF:00:00:00") is None
    first, last = min(table), max(table)
    assert get_vendor(first + "000000") == table[first]
    assert get_vendor(last + "000000") == table[last]


@pytest.mark.asyncio
async def test_malformed_macs() -> None:
    """Short, non-hex or oddly separated MACs return None instead of raising."""
    await async_load()
    assert get_vendor("") is None
    assert get_vendor("00:00") is None
    assert get_vendor("00-00-00-00-00-00") is None
    assert get_vendor("zz:00:00:00:00:00") is None
    assert get_vendor("000000") == "XEROX CORPORATION"
    assert get_vendor("000000112233") == "XEROX CORPORATION"


def test_bytes_fallback_when_mmap_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """If mmap is unavailable the data is read into bytes and lookups still work."""

    def _fail(*args, **kwargs):
        raise OSError("no mmap")

    monkeypatch.setattr(mmap, "mmap", _fail)
    manager = aiooui.OUIManager()
    data = manager._load_oui_data()
    assert isinstance(data, bytes)
    manager._attach(data)
    assert manager.get_vendor("00:00:00:00:00:00") == "XEROX CORPORATION"
    assert manager.get_vendor("FF:FF:FF:00:00:00") is None


def test_big_endian_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """On big-endian hosts the arrays are unpacked instead of viewed in place."""
    monkeypatch.setattr(sys, "byteorder", "big")
    manager = aiooui.OUIManager()
    manager._attach(_DATA_FILE.read_bytes())
    assert isinstance(manager._keys, tuple)
    assert manager.get_vendor("00:00:00:00:00:00") == "XEROX CORPORATION"
    assert manager.get_vendor("FF:FF:FF:00:00:00") is None


def test_invalid_table_rejected() -> None:
    """A file with the wrong magic or a truncated header is refused."""
    manager = aiooui.OUIManager()
    with pytest.raises(RuntimeError):
        manager._attach(b"OUI0" + struct.pack("<I", 0))
    with pytest.raises(RuntimeError):
        manager._attach(struct.pack("<4sI", b"OUI1", 1000))


def _reference_table() -> dict[str, str]:
    """Decode oui.data independently of the runtime search."""
    raw = _DATA_FILE.read_bytes()
    magic, count = struct.unpack_from("<4sI", raw)
    assert magic == b"OUI1"
    keys = struct.unpack_from(f"<{count}I", raw, 8)
    offsets = struct.unpack_from(f"<{count}I", raw, 8 + 4 * count)
    blob = raw[8 + 8 * count :]
    table = {}
    for key, offset in zip(keys, offsets):
        end = blob.index(b"\n", offset)
        table[f"{key:06X}"] = blob[offset:end].decode()
    return table


def test_data_file_is_valid() -> None:
    """The binary search needs sorted, unique 24-bit keys and valid vendor offsets."""
    raw = _DATA_FILE.read_bytes()
    magic, count = struct.unpack_from("<4sI", raw)
    assert magic == b"OUI1"
    keys = struct.unpack_from(f"<{count}I", raw, 8)
    offsets = struct.unpack_from(f"<{count}I", raw, 8 + 4 * count)
    blob = raw[8 + 8 * count :]
    assert count > 30000
    assert list(keys) == sorted(
        keys
    ), "oui.data must be sorted by OUI (see build_oui.py)"
    assert len(keys) == len(set(keys)), "duplicate OUI in oui.data"
    assert all(0 <= k < 1 << 24 for k in keys), "OUI keys must be 24-bit"
    assert blob.endswith(b"\n")
    line_starts = {0}
    pos = 0
    while (nl := blob.find(b"\n", pos)) != -1:
        line_starts.add(nl + 1)
        pos = nl + 1
    assert all(o in line_starts and o < len(blob) for o in offsets)
    blob.decode()


@pytest.mark.asyncio
async def test_random_macs_match_reference() -> None:
    """Random MACs (hits and misses, mixed case) agree with the reference decoder."""
    await async_load()
    table = _reference_table()
    rng = random.Random(20260924)  # noqa: S311 - reproducible test data
    known = list(table)
    hits = misses = 0
    for i in range(20000):
        oui = rng.choice(known) if i % 2 else f"{rng.randrange(1 << 24):06X}"
        tail = [f"{rng.randrange(256):02x}" for _ in range(3)]
        mac = ":".join([oui[0:2], oui[2:4], oui[4:6], *tail])
        if rng.random() < 0.5:
            mac = mac.lower()
        expected = table.get(oui)
        assert get_vendor(mac) == expected, mac
        if expected is None:
            misses += 1
        else:
            hits += 1
    assert hits > 9000
    assert misses > 1000


def test_pack_and_lookup_edge_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Small synthetic tables: single entry, ends, "=" in vendor, shared vendors."""
    build_oui = _import_build_oui(monkeypatch)

    def load(table: dict[int, bytes]) -> aiooui.OUIManager:
        manager = aiooui.OUIManager()
        manager._attach(build_oui._pack(table))
        return manager

    one = load({0x000001: b"ONE"})
    assert one.get_vendor("00:00:01:aa:bb:cc") == "ONE"
    assert one.get_vendor("00:00:00:aa:bb:cc") is None
    assert one.get_vendor("00:00:02:aa:bb:cc") is None

    many = load({0x0000FF: b"LAST", 0x00000A: b"B=C", 0x000001: b"A", 0x000002: b"A"})
    assert many.get_vendor("00:00:01:00:00:00") == "A"
    assert many.get_vendor("00:00:02:00:00:00") == "A"
    assert many.get_vendor("00:00:0A:00:00:00") == "B=C"
    assert many.get_vendor("00:00:FF:00:00:00") == "LAST"
    for miss in ("00:00:00", "00:00:03", "00:01:00", "FF:FF:FF"):
        assert many.get_vendor(miss + ":00:00:00") is None

    empty = load({})
    assert empty.get_vendor("00:00:00:00:00:00") is None
    with pytest.raises(ValueError, match="Unexpected vendor"):
        build_oui._pack({0x000001: b"bad\nvendor"})
    with pytest.raises(ValueError, match="Unexpected vendor"):
        build_oui._pack({0x000001: b""})
    with pytest.raises(UnicodeDecodeError):
        build_oui._pack({0x000001: b"\xff"})


def _import_build_oui(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import a fresh copy of build_oui."""
    monkeypatch.delitem(sys.modules, "build_oui", raising=False)
    import build_oui

    return build_oui


def test_build_rejects_malformed_oui(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed IEEE entry raises before oui.data is written."""
    build_oui = _import_build_oui(monkeypatch)

    with pytest.raises(ValueError, match="Unexpected OUI"):
        build_oui._update_from_oui_content(b"00-00-0X   (base 16)\t\tBROKEN\n")


def test_build_parses_ieee_format(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The IEEE text is parsed, sorted and written in the binary layout."""
    build_oui = _import_build_oui(monkeypatch)
    target = tmp_path / "src" / "aiooui" / "oui.data"
    target.parent.mkdir(parents=True)
    monkeypatch.setattr(build_oui, "__file__", str(tmp_path / "build_oui.py"))
    build_oui._update_from_oui_content(
        b"00-00-0A   (hex)\t\tOMRON\n"
        b"00000A     (base 16)\t\tOMRON TATEISI ELECTRONICS CO.\n"
        b"\n"
        b"00-00-00   (hex)\t\tXEROX\n"
        b"000000     (base 16)\t\tXEROX CORPORATION\n"
    )
    manager = aiooui.OUIManager()
    manager._attach(target.read_bytes())
    assert manager._count == 2
    assert manager.get_vendor("00:00:00:11:22:33") == "XEROX CORPORATION"
    assert manager.get_vendor("00:00:0A:11:22:33") == "OMRON TATEISI ELECTRONICS CO."


def test_build_does_not_retry_malformed_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation errors are not retried or swallowed by the download loop."""
    build_oui = _import_build_oui(monkeypatch)

    calls = []

    def fail_requests():
        calls.append("requests")
        raise ValueError("Unexpected OUI b'00000X'")

    monkeypatch.setattr(build_oui, "_regenerate_ouis_requests", fail_requests)
    monkeypatch.setattr(build_oui.time, "sleep", lambda s: calls.append("sleep"))
    with pytest.raises(ValueError):
        build_oui.main()
    assert calls == ["requests"]


def test_build_falls_back_or_fails_on_network_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Network errors retry with backoff, then keep the file unless required."""
    build_oui = _import_build_oui(monkeypatch)

    sleeps: list[int] = []

    def fail_requests():
        raise OSError("connection refused")

    async def fail_aiohttp():
        raise OSError("connection refused")

    monkeypatch.setattr(build_oui, "_regenerate_ouis_requests", fail_requests)
    monkeypatch.setattr(build_oui, "_regenerate_ouis_aiohttp", fail_aiohttp)
    monkeypatch.setattr(build_oui.time, "sleep", sleeps.append)
    monkeypatch.delenv("AIOOUI_REQUIRE_REGENERATE", raising=False)
    build_oui.main()
    assert sleeps == [5, 10, 20, 40, 80, 160]

    monkeypatch.setenv("AIOOUI_REQUIRE_REGENERATE", "true")
    with pytest.raises(RuntimeError, match="Failed to regenerate"):
        build_oui.main()
