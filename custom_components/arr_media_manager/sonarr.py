from __future__ import annotations

from typing import Any

from .api import LookupResult
from .base_adapter import BaseARRAdapter


class SonarrAdapter(BaseARRAdapter):
    """Adapter for Sonarr API behavior."""

    application = "sonarr"
    api_version = "/api/v3"
    lookup_endpoint = "/api/v3/series/lookup"
    library_endpoint = "/api/v3/series"
    queue_endpoint = "/api/v3/queue"
    health_endpoint = "/api/v3/health"
    disk_space_endpoint = "/api/v3/diskspace"
    quality_profile_endpoint = "/api/v3/qualityprofile"
    root_folder_endpoint = "/api/v3/rootfolder"
    command_endpoint = "/api/v3/command"
    media_endpoint = "/api/v3/series"

    @property
    def supported_actions(self) -> set[str]:
        return {
            "rss_sync",
            "refresh_library",
            "rescan_folders",
            "refresh_quality_profiles",
            "refresh_root_folders",
            "refresh_all_series",
            "search_monitored_episodes",
        }

    @property
    def monitoring_options(self) -> dict[str, str]:
        return {
            "all": "All episodes",
            "future": "Future episodes",
            "missing": "Missing episodes",
            "existing": "Existing episodes",
            "first": "First season",
            "latest": "Latest season",
            "none": "None",
        }

    def build_media_payload(
        self,
        lookup_result: dict[str, Any] | LookupResult,
        *,
        root_folder: str | None = None,
        quality_profile: str | int | None = None,
        monitoring_mode: str | None = None,
        search_after_add: bool = False,
    ) -> dict[str, Any]:
        title = lookup_result.title if isinstance(lookup_result, LookupResult) else lookup_result.get("title") or lookup_result.get("name")
        tvdb_id = lookup_result.foreign_id if isinstance(lookup_result, LookupResult) else lookup_result.get("tvdbId")
        imdb_id = None if isinstance(lookup_result, LookupResult) else lookup_result.get("imdbId")
        images = [] if isinstance(lookup_result, LookupResult) else lookup_result.get("images", [])
        profile_id = quality_profile if isinstance(quality_profile, int) else None
        payload: dict[str, Any] = {
            "title": title,
            "images": images,
            "monitored": True,
            "addOptions": {
                "searchForMissingEpisodes": search_after_add,
                "ignoreEpisodesWithFiles": False,
                "ignoreEpisodesWithoutFiles": False,
            },
        }
        if root_folder:
            payload["rootFolderPath"] = root_folder
        if profile_id is not None:
            payload["qualityProfileId"] = profile_id
        if monitoring_mode:
            payload["monitor"] = monitoring_mode
        if tvdb_id is not None:
            payload["tvdbId"] = int(tvdb_id)
        if imdb_id is not None:
            payload["imdbId"] = imdb_id
        return payload

    async def async_search_monitored_episodes(self) -> dict[str, Any]:
        return await self.async_trigger_command("MissingEpisodeSearch")

    async def async_search_added_media(self, media_id: str | int) -> dict[str, Any]:
        return await self.async_trigger_command("MissingEpisodeSearch", seriesId=int(media_id))

    async def async_refresh_all_series(self) -> dict[str, Any]:
        return await self.async_trigger_command("RefreshSeries")

    async def async_delete_media(self, media_id: str | int, *, delete_files: bool = False, add_import_exclusion: bool = False) -> dict[str, Any]:
        return await self.async_trigger_command("DeleteSeries", seriesId=int(media_id), deleteFiles=delete_files, addImportExclusion=add_import_exclusion)
