from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .api import (
    ArrApiClient,
    ArrConflictError,
    ArrNotFoundError,
    ArrUnsupportedOperationError,
    LookupResult,
    normalize_lookup_result,
    normalize_lookup_results,
)


class BaseARRAdapter(ABC):
    """Base adapter with application-aware endpoint definitions."""

    application: str
    api_version: str
    lookup_endpoint: str
    library_endpoint: str
    queue_endpoint: str
    health_endpoint: str
    disk_space_endpoint: str
    quality_profile_endpoint: str
    root_folder_endpoint: str
    command_endpoint: str
    media_endpoint: str

    def __init__(self, client: ArrApiClient) -> None:
        self.client = client

    @property
    def supported_actions(self) -> set[str]:
        return {
            "rss_sync",
            "refresh_library",
            "rescan_folders",
            "refresh_quality_profiles",
            "refresh_root_folders",
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

    @abstractmethod
    def build_media_payload(
        self,
        lookup_result: dict[str, Any],
        *,
        root_folder: str | None = None,
        quality_profile: str | int | None = None,
        monitoring_mode: str | None = None,
        search_after_add: bool = False,
    ) -> dict[str, Any]:
        """Build the application-specific payload for adding media."""

    async def async_get_system_status(self) -> dict[str, Any]:
        return await self.client.get(f"{self.api_version}/system/status")

    async def async_get_queue(self) -> dict[str, Any]:
        return await self.client.get(self.queue_endpoint)

    async def async_get_health_issues(self) -> list[dict[str, Any]]:
        return await self.client.get(self.health_endpoint)

    async def async_get_disk_space(self) -> list[dict[str, Any]]:
        return await self.client.get(self.disk_space_endpoint)

    async def async_get_quality_profiles(self) -> list[dict[str, Any]]:
        return await self.client.get(self.quality_profile_endpoint)

    async def async_get_root_folders(self) -> list[dict[str, Any]]:
        return await self.client.get(self.root_folder_endpoint)

    async def async_get_library_summary(self) -> dict[str, Any]:
        return await self.client.get(self.library_endpoint)

    async def async_lookup(self, query: str, *, max_results: int = 10) -> list[LookupResult]:
        raw_results = await self.client.get(
            self.lookup_endpoint,
            params={"term": query, "limit": max_results},
        )
        return normalize_lookup_results(raw_results, self.application)

    async def async_lookup_raw(self, query: str, *, max_results: int = 10) -> list[dict[str, Any]]:
        raw_results = await self.client.get(
            self.lookup_endpoint,
            params={"term": query, "limit": max_results},
        )
        if isinstance(raw_results, dict):
            return [raw_results]
        if isinstance(raw_results, list):
            return [item for item in raw_results if isinstance(item, dict)]
        return []

    async def async_add_media(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self.client.post(self.media_endpoint, json_body=payload)
        return result if isinstance(result, dict) else {}

    async def async_resolve_lookup(self, lookup_id: str) -> dict[str, Any]:
        """Resolve a stable lookup ID to the current complete ARR lookup payload."""
        if not lookup_id or ":" not in lookup_id:
            raise ArrNotFoundError("Invalid lookup_id")
        _, identifier = lookup_id.split(":", 1)
        candidates = await self.async_lookup_raw(identifier, max_results=50)
        matches = []
        for item in candidates:
            normalized = normalize_lookup_result(item, self.application)
            if normalized and normalized.lookup_id == lookup_id:
                matches.append(item)
        if not matches:
            raise ArrNotFoundError(f"Lookup result no longer exists: {lookup_id}")
        if len(matches) > 1:
            raise ArrConflictError(f"Lookup ID is not unique: {lookup_id}")
        return matches[0]

    async def async_search_added_media(self, media_id: str | int) -> dict[str, Any]:
        raise ArrUnsupportedOperationError(f"Search after add is not supported for {self.application}")

    async def async_refresh_library(self) -> dict[str, Any]:
        return await self.client.post(self.command_endpoint, json_body={"name": "RefreshSeries" if self.application == "sonarr" else "RefreshMovie" if self.application == "radarr" else "RefreshArtist"})

    async def async_trigger_command(self, command: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"name": command}
        payload.update(kwargs)
        return await self.client.post(self.command_endpoint, json_body=payload)

    async def async_delete_media(self, media_id: str | int, *, delete_files: bool = False, add_import_exclusion: bool = False) -> dict[str, Any]:
        raise ArrUnsupportedOperationError(f"Delete is not supported for {self.application}")

    async def async_search_and_add(
        self,
        query: str,
        *,
        lookup_results: list[dict[str, Any] | LookupResult] | None = None,
        root_folder: str | None = None,
        quality_profile: str | int | None = None,
        monitoring_mode: str | None = None,
        search_after_add: bool = False,
        exact_match: bool = False,
        year: int | None = None,
        foreign_id: str | None = None,
    ) -> dict[str, Any]:
        """Resolve the best match, build the payload, and add it to the ARR library."""
        matches = (
            lookup_results
            if lookup_results is not None
            else await self.async_lookup_raw(query, max_results=10)
        )
        selected = self._choose_lookup_result(
            query=query,
            matches=matches,
            exact_match=exact_match,
            year=year,
            foreign_id=foreign_id,
        )
        if selected is None:
            raise ArrUnsupportedOperationError(f"No media found for query: {query}")

        payload = self.build_media_payload(
            selected,
            root_folder=root_folder,
            quality_profile=quality_profile,
            monitoring_mode=monitoring_mode,
            search_after_add=search_after_add,
        )
        return await self.async_add_media(payload)

    def _choose_lookup_result(
        self,
        *,
        query: str,
        matches: list[dict[str, Any] | LookupResult],
        exact_match: bool,
        year: int | None,
        foreign_id: str | None,
    ) -> dict[str, Any] | LookupResult | None:
        if not matches:
            return None

        query_norm = self._normalize_text(query)
        foreign_id_norm = self._normalize_text(foreign_id) if foreign_id else None
        year_norm = year

        def score(item: dict[str, Any] | LookupResult) -> tuple[int, int, int]:
            title, item_year, item_foreign, already_exists = self._match_fields(item)

            score_value = 0
            if foreign_id_norm and item_foreign == foreign_id_norm:
                score_value += 100
            if query_norm and title == query_norm:
                score_value += 50
            if query_norm and query_norm in title:
                score_value += 20
            if year_norm is not None and item_year == year_norm:
                score_value += 30
            if already_exists:
                score_value -= 10
            return (score_value, 1 if item_year == year_norm else 0, 0 if not title else 1)

        if exact_match:
            if foreign_id_norm:
                for item in matches:
                    _, _, item_foreign, _ = self._match_fields(item)
                    if item_foreign == foreign_id_norm:
                        return item
            for item in matches:
                title, item_year, _, _ = self._match_fields(item)
                if title == query_norm and (year_norm is None or item_year == year_norm):
                    return item
            return matches[0]

        best = sorted(matches, key=score, reverse=True)[0]
        return best

    def _match_fields(
        self,
        item: dict[str, Any] | LookupResult,
    ) -> tuple[str, int | None, str, bool]:
        if isinstance(item, LookupResult):
            return (
                self._normalize_text(item.title),
                item.year,
                self._normalize_text(item.foreign_id),
                item.already_exists,
            )
        return (
            self._normalize_text(item.get("title") or item.get("name") or ""),
            item.get("year"),
            self._normalize_text(
                item.get("foreignId")
                or item.get("tvdbId")
                or item.get("tmdbId")
                or item.get("imdbId")
                or ""
            ),
            bool(item.get("existing")),
        )

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().casefold()

    async def async_get_lookup_by_foreign_id(self, external_id: str) -> list[dict[str, Any]]:
        return []

    async def async_get_media_by_id(self, media_id: str | int) -> dict[str, Any]:
        raise ArrUnsupportedOperationError(f"Get media by id is not supported for {self.application}")
