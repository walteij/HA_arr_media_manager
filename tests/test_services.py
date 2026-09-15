from __future__ import annotations

import pytest
from homeassistant.core import SupportsResponse

from custom_components.arr_media_manager.services import (
    async_handle_lookup,
    async_handle_search_and_add,
    async_register_services,
)


class LookupAdapter:
    application = "radarr"

    async def async_lookup(self, query: str, *, max_results: int) -> list[dict[str, str]]:
        return [
            {
                "id": 42,
                "title": query,
                "year": 2024,
                "foreignId": "tmdb-42",
                "max_results": max_results,
            }
        ]

    async def async_search_and_add(self, query: str, **kwargs: object) -> dict[str, object]:
        return {"query": query, "search_after_add": kwargs["search_after_add"]}


class FakeEntry:
    entry_id = "entry-id"


class FakeConfigEntries:
    def async_get_entry(self, entry_id: str) -> FakeEntry:
        assert entry_id == "entry-id"
        return FakeEntry()


class FakeServices:
    def __init__(self) -> None:
        self.registered: dict[str, SupportsResponse] = {}

    def has_service(self, domain: str, service: str) -> bool:
        return service in self.registered

    def async_register(self, domain: str, service: str, handler: object, *, schema: object, supports_response: SupportsResponse) -> None:
        self.registered[service] = supports_response


class FakeHass:
    config_entries = FakeConfigEntries()
    data = {"arr_media_manager": {"entry-id": {"adapter": LookupAdapter()}}}


class FakeCall:
    data = {
        "config_entry_id": "entry-id",
        "query": "Dune",
        "max_results": 5,
    }


@pytest.mark.asyncio
async def test_lookup_dispatches_to_selected_application() -> None:
    result = await async_handle_lookup(FakeHass(), FakeCall())

    assert result == {
        "count": 1,
        "results": [
            {
                "id": 42,
                "title": "Dune",
                "year": 2024,
                "media_type": None,
                "foreign_id": "tmdb-42",
                "overview": None,
                "poster_url": None,
                "existing": False,
                "application_id": 42,
                "raw": {
                    "id": 42,
                    "title": "Dune",
                    "year": 2024,
                    "foreignId": "tmdb-42",
                    "max_results": 5,
                },
            }
        ],
    }


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_search_and_add_uses_config_entry_application() -> None:
    FakeCall.data = {
        "config_entry_id": "entry-id",
        "query": "Dune",
        "search_after_add": True,
    }

    result = await async_handle_search_and_add(FakeHass(), FakeCall())

    assert result == {"status": "ok", "result": {"query": "Dune", "search_after_add": True}}


@pytest.mark.asyncio
async def test_services_register_response_support() -> None:
    services = FakeServices()
    hass = type("Hass", (), {"services": services})()

    await async_register_services(hass)

    assert services.registered == {
        "lookup": SupportsResponse.ONLY,
        "add_media": SupportsResponse.OPTIONAL,
        "search_and_add": SupportsResponse.OPTIONAL,
        "trigger_search": SupportsResponse.OPTIONAL,
        "refresh": SupportsResponse.OPTIONAL,
        "delete_media": SupportsResponse.OPTIONAL,
    }
