from __future__ import annotations

from typing import Any

from .api import LookupResult
from .base_adapter import BaseARRAdapter


class RadarrAdapter(BaseARRAdapter):
    """Adapter for Radarr API behavior."""

    application = "radarr"
    api_version = "/api/v3"
    lookup_endpoint = "/api/v3/movie/lookup"
    library_endpoint = "/api/v3/movie"
    queue_endpoint = "/api/v3/queue"
    health_endpoint = "/api/v3/health"
    disk_space_endpoint = "/api/v3/diskspace"
    quality_profile_endpoint = "/api/v3/qualityprofile"
    root_folder_endpoint = "/api/v3/rootfolder"
    command_endpoint = "/api/v3/command"
    media_endpoint = "/api/v3/movie"

    @property
    def supported_actions(self) -> set[str]:
        return {
            "rss_sync",
            "refresh_library",
            "rescan_folders",
            "refresh_quality_profiles",
            "refresh_root_folders",
            "refresh_all_movies",
            "search_monitored_movies",
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
        tmdb_id = lookup_result.foreign_id if isinstance(lookup_result, LookupResult) else lookup_result.get("tmdbId")
        imdb_id = None if isinstance(lookup_result, LookupResult) else lookup_result.get("imdbId")
        images = [] if isinstance(lookup_result, LookupResult) else lookup_result.get("images", [])
        payload: dict[str, Any] = {
            "title": title,
            "images": images,
            "monitored": True,
            "minimumAvailability": "released",
            "addOptions": {
                "searchForMovie": search_after_add,
                "ignoreEpisodesWithFiles": False,
            },
        }
        if root_folder:
            payload["rootFolderPath"] = root_folder
        if quality_profile is not None:
            payload["qualityProfileId"] = int(quality_profile) if isinstance(quality_profile, str) and quality_profile.isdigit() else quality_profile
        if monitoring_mode:
            payload["monitor"] = monitoring_mode
        if tmdb_id is not None:
            payload["tmdbId"] = int(tmdb_id)
        if imdb_id is not None:
            payload["imdbId"] = imdb_id
        return payload

    async def async_search_monitored_movies(self) -> dict[str, Any]:
        return await self.async_trigger_command("MoviesSearch")

    async def async_search_added_media(self, media_id: str | int) -> dict[str, Any]:
        return await self.async_trigger_command("MoviesSearch", movieId=int(media_id))

    async def async_refresh_all_movies(self) -> dict[str, Any]:
        return await self.async_trigger_command("RefreshMovie")

    async def async_delete_media(self, media_id: str | int, *, delete_files: bool = False, add_import_exclusion: bool = False) -> dict[str, Any]:
        return await self.async_trigger_command("DeleteMovie", movieId=int(media_id), deleteFiles=delete_files, addImportExclusion=add_import_exclusion)
