from __future__ import annotations

import pytest

from custom_components.arr_media_manager.api import LookupResult
from custom_components.arr_media_manager.base_adapter import BaseARRAdapter
from custom_components.arr_media_manager.lidarr import LidarrAdapter
from custom_components.arr_media_manager.radarr import RadarrAdapter
from custom_components.arr_media_manager.sonarr import SonarrAdapter


class DummyClient:
    def __init__(self, lookup_response=None) -> None:
        self.calls: list[tuple[str, dict | None]] = []
        self.lookup_response = lookup_response

    async def get(self, endpoint: str, *, params=None):
        self.calls.append(("GET", {"endpoint": endpoint, "params": params}))
        if endpoint.endswith("lookup") and self.lookup_response is not None:
            return self.lookup_response
        return []

    async def post(self, endpoint: str, *, json_body=None, params=None):
        self.calls.append(("POST", {"endpoint": endpoint, "json": json_body, "params": params}))
        return json_body


class DummyAdapter(BaseARRAdapter):
    application = "test"
    api_version = "/api/test"
    lookup_endpoint = "/api/test/lookup"
    library_endpoint = "/api/test/library"
    queue_endpoint = "/api/test/queue"
    health_endpoint = "/api/test/health"
    disk_space_endpoint = "/api/test/diskspace"
    quality_profile_endpoint = "/api/test/qualityprofile"
    root_folder_endpoint = "/api/test/rootfolder"
    command_endpoint = "/api/test/command"
    media_endpoint = "/api/test/media"

    def build_media_payload(self, lookup_result, *, root_folder=None, quality_profile=None, monitoring_mode=None, search_after_add=False):
        title = lookup_result.title if isinstance(lookup_result, LookupResult) else lookup_result.get("title")
        return {
            "title": title,
            "rootFolderPath": root_folder,
            "qualityProfileId": quality_profile,
            "monitor": monitoring_mode,
            "searchAfterAdd": search_after_add,
        }


async def test_adapter_search_and_add_uses_exact_match_when_available():
    client = DummyClient()
    adapter = DummyAdapter(client)

    payload = await adapter.async_search_and_add(
        "The Expanse",
        lookup_results=[
            LookupResult(lookup_id="tvdb:1", title="The Expanse", year=2015),
            LookupResult(lookup_id="tvdb:2", title="The Expanse 2", year=2017),
        ],
        root_folder="/downloads",
        quality_profile="1080p",
        monitoring_mode="future",
        search_after_add=True,
        exact_match=True,
    )

    assert payload["title"] == "The Expanse"
    assert payload["rootFolderPath"] == "/downloads"
    assert payload["monitor"] == "future"
    assert payload["searchAfterAdd"] is True
    assert client.calls[-1][1]["json"]["title"] == "The Expanse"


async def test_sonarr_adapter_build_media_payload_uses_tvdb_id():
    adapter = SonarrAdapter(DummyClient())
    payload = adapter.build_media_payload(
        LookupResult(lookup_id="tvdb:12345", title="The Expanse", foreign_id="12345"),
        root_folder="/tv",
        quality_profile=7,
        monitoring_mode="all",
        search_after_add=True,
    )

    assert payload["title"] == "The Expanse"
    assert payload["rootFolderPath"] == "/tv"
    assert payload["qualityProfileId"] == 7
    assert payload["monitor"] == "all"
    assert payload["addOptions"]["searchForMissingEpisodes"] is True
    assert payload["tvdbId"] == 12345


async def test_all_arr_lookup_adapters_return_normalized_lists():
    for adapter in (
        SonarrAdapter(DummyClient()),
        RadarrAdapter(DummyClient()),
        LidarrAdapter(DummyClient()),
    ):
        results = await adapter.async_lookup("Dune")
        assert isinstance(results, list)


async def test_async_lookup_normalizes_all_supported_response_shapes():
    responses = [
        [{"tmdbId": 1, "title": "Dune"}, {"tmdbId": 2, "title": "Dune Part Two"}],
        [],
    ]

    for response in responses:
        adapter = RadarrAdapter(DummyClient(response))
        results = await adapter.async_lookup("Dune")
        assert isinstance(results, list)
        assert all(result.lookup_id.startswith("tmdb:") for result in results)


async def test_async_lookup_rejects_dictionary_shaped_top_level_response():
    adapter = RadarrAdapter(DummyClient({"tmdbId": 1, "title": "Dune"}))

    from custom_components.arr_media_manager.api import ArrInvalidResponseError

    with pytest.raises(ArrInvalidResponseError, match="Expected ARR lookup endpoint to return a list"):
        await adapter.async_lookup("Dune")


def test_lookup_result_exact_match_uses_attributes():
    adapter = DummyAdapter(DummyClient())
    result = adapter._choose_lookup_result(
        query="Dune",
        matches=[
            LookupResult(lookup_id="tmdb:2", title="Dune Part Two", year=2024),
            LookupResult(lookup_id="tmdb:1", title="Dune", year=2021),
        ],
        exact_match=True,
        year=None,
        foreign_id=None,
    )

    assert isinstance(result, LookupResult)
    assert result.lookup_id == "tmdb:1"


def test_lookup_result_year_comparison_uses_attributes():
    adapter = DummyAdapter(DummyClient())
    result = adapter._choose_lookup_result(
        query="Dune",
        matches=[
            LookupResult(lookup_id="tmdb:1", title="Dune", year=1984),
            LookupResult(lookup_id="tmdb:2", title="Dune", year=2021),
        ],
        exact_match=True,
        year=2021,
        foreign_id=None,
    )

    assert isinstance(result, LookupResult)
    assert result.year == 2021


def test_lookup_result_foreign_id_comparison_uses_attributes():
    adapter = DummyAdapter(DummyClient())
    result = adapter._choose_lookup_result(
        query="Dune",
        matches=[
            LookupResult(lookup_id="tmdb:1", title="Dune", foreign_id="111"),
            LookupResult(lookup_id="tmdb:2", title="Dune", foreign_id="222"),
        ],
        exact_match=True,
        year=None,
        foreign_id="222",
    )

    assert isinstance(result, LookupResult)
    assert result.foreign_id == "222"


async def test_search_and_add_accepts_lookup_result_instances():
    adapter = DummyAdapter(DummyClient())

    result = await adapter.async_search_and_add(
        "Dune",
        lookup_results=[LookupResult(lookup_id="tmdb:1", title="Dune", year=2021)],
        exact_match=True,
    )

    assert result["title"] == "Dune"
