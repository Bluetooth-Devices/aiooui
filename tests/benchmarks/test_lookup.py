"""CodSpeed benchmarks for loading the OUI table and looking up vendors."""

from __future__ import annotations

import mmap
import pathlib
import random

from pytest_codspeed import BenchmarkFixture

import aiooui

_SAMPLE = 1000
_DATA_FILE = pathlib.Path(aiooui.__file__).parent.joinpath("oui.data")


def _known_ouis() -> list[str]:
    """Every OUI in the data file, in file order."""
    raw = _DATA_FILE.read_bytes().rstrip(b"\n")
    return [line.partition(b"=")[0].decode() for line in raw.split(b"\n")]


def _mac(oui: str, tail: str = "11:22:33") -> str:
    return f"{oui[0:2]}:{oui[2:4]}:{oui[4:6]}:{tail}"


_KNOWN = _known_ouis()
_STEP = max(len(_KNOWN) // _SAMPLE, 1)
HITS = [_mac(oui) for oui in _KNOWN[::_STEP][:_SAMPLE]]
HITS_LOWER = [mac.lower() for mac in HITS]

_rng = random.Random(20260925)  # noqa: S311 - reproducible benchmark data
_known_set = set(_KNOWN)
MISSES: list[str] = []
while len(MISSES) < _SAMPLE:
    oui = f"{_rng.randrange(1 << 24):06X}"
    if oui not in _known_set:
        MISSES.append(_mac(oui))

MIXED = [mac for pair in zip(HITS, MISSES) for mac in pair]


def _loaded_manager() -> aiooui.OUIManager:
    manager = aiooui.OUIManager()
    manager._oui_to_vendor = manager._load_oui_data()
    return manager


def test_load_oui_data(benchmark: BenchmarkFixture) -> None:
    """
    Map the data file and touch every page, as async_load does in the executor.

    The benchmark runs many times, so the file is in the page cache after the
    first iteration; this measures a warm load. CodSpeed counts instructions,
    so disk I/O is not part of the result either way.
    """
    manager = aiooui.OUIManager()

    @benchmark
    def _run() -> None:
        data = manager._load_oui_data()
        if isinstance(data, mmap.mmap):
            data.close()


def test_get_vendor_hits(benchmark: BenchmarkFixture) -> None:
    """Look up known OUIs spread across the whole table."""
    manager = _loaded_manager()
    assert all(manager.get_vendor(mac) is not None for mac in HITS)

    @benchmark
    def _run() -> None:
        for mac in HITS:
            manager.get_vendor(mac)


def test_get_vendor_hits_lowercase(benchmark: BenchmarkFixture) -> None:
    """Same lookups with lowercase MACs, which need uppercasing first."""
    manager = _loaded_manager()

    @benchmark
    def _run() -> None:
        for mac in HITS_LOWER:
            manager.get_vendor(mac)


def test_get_vendor_misses(benchmark: BenchmarkFixture) -> None:
    """Look up OUIs that are not in the table."""
    manager = _loaded_manager()
    assert all(manager.get_vendor(mac) is None for mac in MISSES)

    @benchmark
    def _run() -> None:
        for mac in MISSES:
            manager.get_vendor(mac)


def test_get_vendor_mixed(benchmark: BenchmarkFixture) -> None:
    """Alternate hits and misses, closer to a scan of unknown devices."""
    manager = _loaded_manager()

    @benchmark
    def _run() -> None:
        for mac in MIXED:
            manager.get_vendor(mac)
