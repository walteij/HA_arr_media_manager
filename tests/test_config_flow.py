from __future__ import annotations

import pytest

from custom_components.arr_media_manager.config_flow import (
    ARRMediaManagerConfigFlow,
    validate_base_url,
)
from custom_components.arr_media_manager.const import (
    APPLICATION_SONARR,
    CONF_API_KEY,
    CONF_APPLICATION,
    CONF_BASE_URL,
    CONF_INSTANCE_NAME,
    CONF_TIMEOUT,
    CONF_VERIFY_SSL,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("  http://example.com:8989/  ", "http://example.com:8989"),
        ("https://example.com/", "https://example.com"),
    ],
)
def test_validate_base_url_normalizes(url: str, expected: str) -> None:
    assert validate_base_url(url) == expected


def test_validate_base_url_rejects_invalid_scheme() -> None:
    with pytest.raises(ValueError):
        validate_base_url("ftp://example.com")


def test_config_flow_schema_contains_setup_fields() -> None:
    schema = ARRMediaManagerConfigFlow()._get_schema()

    result = schema(
        {
            CONF_APPLICATION: APPLICATION_SONARR,
            CONF_INSTANCE_NAME: "Sonarr",
            CONF_BASE_URL: "http://example.com:8989",
            CONF_API_KEY: "secret",
            CONF_VERIFY_SSL: True,
            CONF_TIMEOUT: 30,
        }
    )

    assert result[CONF_APPLICATION] == APPLICATION_SONARR
    assert result[CONF_TIMEOUT] == 30
