from __future__ import annotations

import pytest

from custom_components.arr_media_manager.services import async_handle_lookup


class LookupAdapter:
    application = "radarr"

    async def async_lookup(self, query: str, *, max_results: int) -> list[dict[str, str]]:
        return [{"query": query, "max_results": max_results}]


class FakeEntry:
    entry_id = "entry-id"


class FakeConfigEntries:
    def async_get_entry(self, entry_id: str) -> FakeEntry:
        assert entry_id == "entry-id"
        return FakeEntry()


class FakeServices:
    pass


class FakeHass:
    config_entries = FakeConfigEntries()
    data = {"arr_media_manager": {"entry-id": {"adapter": LookupAdapter()}}}


class FakeCall:
    data = {
        "config_entry_id": "entry-id",
        "application": "radarr",
        "query": "Dune",
        "max_results": 5,
    }


@pytest.mark.asyncio
async def test_lookup_dispatches_to_selected_application() -> None:
    result = await async_handle_lookup(FakeHass(), FakeCall())

    assert result == {"count": 1, "results": [{"query": "Dune", "max_results": 5}]}


@pytest.mark.asyncio
async def test_lookup_rejects_application_mismatch() -> None:
    FakeCall.data = {**FakeCall.data, "application": "sonarr"}

    with pytest.raises(ValueError, match="does not match"):
        await async_handle_lookup(FakeHass(), FakeCall())
