from __future__ import annotations

import pytest


@pytest.fixture
def mock_entry():
    return {
        "application": "sonarr",
        "instance_name": "Test Sonarr",
        "base_url": "http://example.com:8989",
        "api_key": "test-api-key",
        "verify_ssl": True,
        "timeout": 30,
    }
