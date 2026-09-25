"""Benchmarks for OUI vendor lookups."""

from __future__ import annotations

import random
import struct
from collections.abc import Iterator

import pytest
from pytest_codspeed import BenchmarkFixture

import aiooui
from aiooui import OUIManager


@pytest.fixture(scope="module")
def manager() -> Iterator[OUIManager]:
    """A dedicated, loaded OUI manager (keeps the module-level one untouched)."""
    mgr = OUIManager()
    mgr._attach(mgr._load_oui_data())
    yield mgr


@pytest.fixture
def loaded(monkeypatch: pytest.MonkeyPatch, manager: OUIManager) -> OUIManager:
    """Route the public ``aiooui.get_vendor`` API to the loaded manager."""
    monkeypatch.setattr(aiooui, "_OUI_MANAGER", manager)
    return manager


@pytest.fixture(scope="module")
def bytes_manager() -> OUIManager:
    """A manager over the data file read fully into memory (mmap fallback path)."""
    mgr = OUIManager()
    mgr._attach(aiooui._OUI_DATA_FILE.read_bytes())
    return mgr


def _sample_macs(count: int) -> list[str]:
    """Reproducible mix of known and unknown MACs, in mixed case."""
    raw = aiooui._OUI_DATA_FILE.read_bytes()
    _, n = struct.unpack_from("<4sI", raw)
    known = [f"{key:06X}" for key in struct.unpack_from(f"<{n}I", raw, 8)]
    rng = random.Random(1234)  # noqa: S311 - reproducible benchmark data
    macs = []
    for i in range(count):
        oui = rng.choice(known) if i % 4 else f"{rng.randrange(1 << 24):06X}"
        tail = [f"{rng.randrange(256):02x}" for _ in range(3)]
        mac = ":".join([oui[0:2], oui[2:4], oui[4:6], *tail])
        macs.append(mac.lower() if i % 2 else mac)
    return macs


MACS_1000 = _sample_macs(1000)


@pytest.mark.parametrize(
    "mac",
    [
        pytest.param("00:00:00:11:22:33", id="first"),
        pytest.param("AC:DE:48:11:22:33", id="middle"),
        pytest.param("fc:ff:aa:11:22:33", id="last-lowercase"),
        pytest.param("FF:FF:FF:11:22:33", id="miss"),
    ],
)
def test_get_vendor(benchmark: BenchmarkFixture, loaded: OUIManager, mac: str) -> None:
    """Single lookup through the public API."""
    result = benchmark(aiooui.get_vendor, mac)
    if mac.startswith("FF"):
        assert result is None


def test_get_vendor_1000_mixed(benchmark: BenchmarkFixture, loaded: OUIManager) -> None:
    """Batch of 1000 lookups: 75% hits, 25% random, mixed case."""
    get_vendor = aiooui.get_vendor

    @benchmark
    def _run() -> None:
        for mac in MACS_1000:
            get_vendor(mac)


def test_bisect_mmap(benchmark: BenchmarkFixture, manager: OUIManager) -> None:
    """200 lookups against the memory-mapped table."""
    macs = MACS_1000[:200]
    get_vendor = manager.get_vendor

    @benchmark
    def _run() -> None:
        for mac in macs:
            get_vendor(mac)


def test_bisect_bytes(benchmark: BenchmarkFixture, bytes_manager: OUIManager) -> None:
    """200 lookups against an in-memory bytes copy (mmap fallback)."""
    macs = MACS_1000[:200]
    get_vendor = bytes_manager.get_vendor

    @benchmark
    def _run() -> None:
        for mac in macs:
            get_vendor(mac)


def test_load_oui_data(benchmark: BenchmarkFixture) -> None:
    """Memory-map and pre-fault the OUI data file, then attach the arrays."""

    @benchmark
    def _run() -> None:
        mgr = OUIManager()
        data = mgr._load_oui_data()
        mgr._attach(data)
        mgr._keys = mgr._offsets = None  # type: ignore[assignment]
        if hasattr(data, "close"):
            data.close()
