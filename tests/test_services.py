from __future__ import annotations

import pytest
from homeassistant.core import SupportsResponse

from custom_components.arr_media_manager.api import LookupResult, normalize_lookup_results
from custom_components.arr_media_manager.services import (
    async_handle_add_media,
    async_handle_lookup,
    async_handle_search_and_add,
    async_register_services,
)
from custom_components.arr_media_manager.sonarr import SonarrAdapter


class LookupAdapter:
    application = "radarr"

    async def async_lookup(self, query: str, *, max_results: int):
        return normalize_lookup_results(
            {
                "id": 42,
                "title": query,
                "year": 2024,
                "tmdbId": "42",
                "overview": "Description",
                "max_results": max_results,
            },
            self.application,
        )

    async def async_search_and_add(self, query: str, **kwargs: object) -> dict[str, object]:
        return {"query": query, "search_after_add": kwargs["search_after_add"]}

    async def async_resolve_lookup(self, lookup_id: str) -> LookupResult:
        return LookupResult(
            lookup_id="tmdb:42",
            title="Dune",
            year=2024,
            media_type="movie",
            foreign_id="42",
        )

    def build_media_payload(self, lookup_result: LookupResult, **kwargs: object) -> dict[str, object]:
        return {"title": lookup_result.title, "tmdbId": lookup_result.foreign_id}

    async def async_add_media(self, payload: dict[str, object]) -> dict[str, object]:
        return {"id": 99, **payload}

    async def async_search_added_media(self, media_id: str | int) -> dict[str, object]:
        return {"id": media_id}


class FakeEntry:
    entry_id = "entry-id"
    data = {"application": "radarr"}


class FakeConfigEntries:
    def async_get_entry(self, entry_id: str) -> FakeEntry:
        assert entry_id == "entry-id"
        return FakeEntry()


class FakeServices:
    def __init__(self) -> None:
        self.registered: dict[str, SupportsResponse] = {}

    def has_service(self, domain: str, service: str) -> bool:
        return service in self.registered

    def async_register(
        self,
        domain: str,
        service: str,
        handler: object,
        *,
        schema: object,
        supports_response: SupportsResponse,
    ) -> None:
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
async def test_lookup_returns_stable_public_response() -> None:
    result = await async_handle_lookup(FakeHass(), FakeCall())

    assert result == {
        "status": "ok",
        "config_entry_id": "entry-id",
        "application": "radarr",
        "query": "Dune",
        "count": 1,
        "results": [
            {
                "lookup_id": "tmdb:42",
                "title": "Dune",
                "year": 2024,
                "media_type": "movie",
                "foreign_id": "42",
                "overview": "Description",
                "poster_url": None,
                "already_exists": False,
            }
        ],
    }


@pytest.mark.asyncio
async def test_add_media_resolves_lookup_and_returns_normalized_response() -> None:
    FakeCall.data = {
        "config_entry_id": "entry-id",
        "lookup_id": "tmdb:42",
        "search_after_add": True,
    }

    result = await async_handle_add_media(FakeHass(), FakeCall())

    assert result == {
        "status": "ok",
        "config_entry_id": "entry-id",
        "application": "radarr",
        "added": True,
        "already_exists": False,
        "search_requested": True,
        "search_accepted": True,
        "media": {
            "media_id": 99,
            "lookup_id": "tmdb:42",
            "title": "Dune",
            "year": 2024,
            "media_type": "movie",
        },
    }


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


class SonarrRuntimeClient:
    async def get(self, endpoint: str, *, params: object = None) -> list[dict[str, object]]:
        assert endpoint == "/api/v3/series/lookup"
        return [
            {"title": "Dune: Prophecy", "year": 2024, "tvdbId": 420658, "images": []},
            {"title": "Dune", "year": 2000, "tvdbId": 265987, "images": []},
        ]

    async def post(self, endpoint: str, *, json_body: dict[str, object] = None, params: object = None) -> dict[str, object]:
        assert endpoint == "/api/v3/series"
        assert json_body["title"] == "Dune"
        assert json_body["tvdbId"] == 265987
        return {"id": 123}


class SonarrEntry:
    entry_id = "sonarr-entry"
    data = {"application": "sonarr"}


class SonarrConfigEntries:
    def async_get_entry(self, entry_id: str) -> SonarrEntry:
        assert entry_id == "sonarr-entry"
        return SonarrEntry()


class SonarrHass:
    config_entries = SonarrConfigEntries()
    data = {
        "arr_media_manager": {
            "sonarr-entry": {"adapter": SonarrAdapter(SonarrRuntimeClient())}
        }
    }


class SonarrCall:
    data = {
        "config_entry_id": "sonarr-entry",
        "query": "Dune",
        "exact_match": True,
        "search_after_add": False,
    }


@pytest.mark.asyncio
async def test_search_and_add_runs_real_sonarr_adapter_pipeline() -> None:
    result = await async_handle_search_and_add(SonarrHass(), SonarrCall())

    assert result == {"status": "ok", "result": {"id": 123}}
