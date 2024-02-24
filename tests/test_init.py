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
