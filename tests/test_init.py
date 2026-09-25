import pytest

from aiooui import async_load, get_vendor, is_loaded


@pytest.mark.asyncio
async def test_get_without_load():
    """Test getting a vendor without loading."""
    assert is_loaded() is False
    with pytest.raises(RuntimeError):
        get_vendor("00:00:00:00:00:00")


@pytest.mark.asyncio
async def test_get_vendor():
    """Test getting a vendor."""
    assert is_loaded() is False
    await async_load()
    assert is_loaded() is True
    await async_load()
    assert is_loaded() is True
    assert get_vendor("00:00:00:00:00:00") == "XEROX CORPORATION"


@pytest.mark.asyncio
async def test_matches_full_table():
    """Every OUI in the data file resolves to the same vendor a dict lookup gives."""
    import pathlib

    import aiooui

    await async_load()
    raw = pathlib.Path(aiooui.__file__).parent.joinpath("oui.data").read_bytes()
    table = {}
    for line in raw.splitlines():
        if not line:
            continue
        raw_oui, _, raw_vendor = line.partition(b"=")
        table[raw_oui.decode()] = raw_vendor.decode("utf-8", "replace")
    for oui, vendor in table.items():
        mac = ":".join((oui[0:2], oui[2:4], oui[4:6], "11", "22", "33"))
        assert get_vendor(mac) == vendor
        assert get_vendor(mac.lower()) == vendor
    assert get_vendor("FF:FF:FF:00:00:00") is None
    first, last = min(table), max(table)
    assert get_vendor(first + "000000") == table[first]
    assert get_vendor(last + "000000") == table[last]


def test_bytes_fallback_when_mmap_fails(monkeypatch):
    """If mmap is unavailable the data is read into bytes and lookups still work."""
    import mmap

    import aiooui

    def _fail(*args, **kwargs):
        raise OSError("no mmap")

    monkeypatch.setattr(mmap, "mmap", _fail)
    data = aiooui.OUIManager()._load_oui_data()
    assert isinstance(data, bytes)
    assert aiooui._bisect(data, b"000000") == "XEROX CORPORATION"
    assert aiooui._bisect(data, b"FFFFFF") is None


def _reference_table() -> dict[str, str]:
    """Parse oui.data the way the old dict implementation did."""
    import pathlib

    import aiooui

    raw = pathlib.Path(aiooui.__file__).parent.joinpath("oui.data").read_bytes()
    table = {}
    for line in raw.decode("utf-8", "replace").splitlines():
        oui, _, vendor = line.partition("=")
        table[oui] = vendor
    return table


def test_data_file_is_sorted():
    """The binary search needs oui.data sorted, with unique 6-hex-digit keys."""
    import pathlib
    import re

    import aiooui

    raw = pathlib.Path(aiooui.__file__).parent.joinpath("oui.data").read_bytes()
    keys = [line.partition(b"=")[0] for line in raw.rstrip(b"\n").split(b"\n")]
    assert all(re.fullmatch(rb"[0-9A-F]{6}", k) for k in keys), "malformed OUI key"
    assert keys == sorted(keys), "oui.data must be sorted by OUI (see build_oui.py)"
    assert len(keys) == len(set(keys)), "duplicate OUI in oui.data"


@pytest.mark.asyncio
async def test_random_macs_match_reference():
    """Random MACs (hits and misses, mixed case) agree with a plain dict lookup."""
    import random

    await async_load()
    table = _reference_table()
    rng = random.Random(20260924)  # noqa: S311 - reproducible test data
    known = list(table)
    hits = misses = 0
    for i in range(20000):
        # half from known prefixes, half fully random (mostly misses between entries)
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


def test_bisect_edge_cases():
    """Small synthetic tables: single entry, ends, "=" in vendor, CRLF, misses."""
    import aiooui

    one = b"000001=ONE"
    assert aiooui._bisect(one, b"000001") == "ONE"
    assert aiooui._bisect(one, b"000000") is None
    assert aiooui._bisect(one, b"000002") is None
    data = b"000001=A\n00000A=B=C\r\n0000FF=LAST"
    assert aiooui._bisect(data, b"000001") == "A"
    assert aiooui._bisect(data, b"00000A") == "B=C"
    assert aiooui._bisect(data, b"0000FF") == "LAST"
    for miss in (b"000000", b"000002", b"000100", b"FFFFFF"):
        assert aiooui._bisect(data, miss) is None
