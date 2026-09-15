from __future__ import annotations

import pytest

from custom_components.arr_media_manager.api import (
    ArrApiError,
    ArrAuthenticationError,
    ArrInvalidResponseError,
    normalize_lookup_result,
    normalize_lookup_results,
)


@pytest.mark.asyncio
async def test_api_raises_auth_error_for_401():
    with pytest.raises(ArrAuthenticationError):
        raise ArrAuthenticationError("Unauthorized")


@pytest.mark.asyncio
async def test_api_raises_invalid_response_for_bad_json():
    with pytest.raises(ArrInvalidResponseError):
        raise ArrInvalidResponseError("Malformed response")


@pytest.mark.asyncio
async def test_api_error_message():
    err = ArrApiError("Test error")
    assert str(err) == "Test error"


def test_normalize_lookup_result_uses_stable_public_id() -> None:
    result = normalize_lookup_result(
        {
            "tmdbId": 335984,
            "title": "Blade Runner 2049",
            "year": 2017,
            "overview": "Description",
            "existing": False,
        },
        "radarr",
    )

    assert result is not None
    assert result.lookup_id == "tmdb:335984"
    assert result.title == "Blade Runner 2049"
    assert result.already_exists is False


def test_normalize_lookup_results_accepts_empty_list() -> None:
    assert normalize_lookup_results([], "radarr") == []


def test_normalize_lookup_results_accepts_single_dictionary() -> None:
    results = normalize_lookup_results({"tmdbId": 1, "title": "Dune"}, "radarr")

    assert len(results) == 1
    assert results[0].lookup_id == "tmdb:1"


def test_normalize_lookup_results_accepts_multiple_dictionaries() -> None:
    results = normalize_lookup_results(
        [{"tmdbId": 1, "title": "Dune"}, {"tmdbId": 2, "title": "Dune Part Two"}],
        "radarr",
    )

    assert [result.lookup_id for result in results] == ["tmdb:1", "tmdb:2"]


def test_normalize_lookup_results_ignores_malformed_response() -> None:
    assert normalize_lookup_results({"unexpected": "shape"}, "radarr") == []
    assert normalize_lookup_results("not a lookup response", "radarr") == []  # type: ignore[arg-type]
