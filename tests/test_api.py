from __future__ import annotations

import pytest

from custom_components.arr_media_manager.api import (
    ArrApiError,
    ArrAuthenticationError,
    ArrInvalidResponseError,
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
