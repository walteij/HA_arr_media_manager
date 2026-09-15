# ARR Media Manager

ARR Media Manager is a Home Assistant custom integration for Sonarr, Radarr, and Lidarr.

## Overview

The integration connects directly to the configured ARR APIs and exposes management functionality not available in the default integrations. It supports lookup, add, search, refresh, and safe delete operations while providing entities that surface useful operational data.

## Supported applications

- Sonarr
- Radarr
- Lidarr

## Features

- UI-based config flow with one config entry per ARR instance
- Application-specific adapters for Sonarr, Radarr, and Lidarr
- Dynamic root folder and quality profile selection
- Coordinators with periodic refresh and error handling
- Sensor, binary sensor, button, and select entities
- Services for lookup, add media, search-and-add, trigger search, refresh, and delete with confirmation
- Redacted diagnostics and secure logging patterns

## Screenshots

This section is intentionally left as a placeholder for screenshots in a normal repository update.

## Requirements

- Home Assistant 2024.12+
- Network access to your Sonarr, Radarr, or Lidarr instance
- A valid API key

## HACS installation

1. Add this repository as a custom repository in HACS.
2. Search for ARR Media Manager and install it.
3. Restart Home Assistant.
4. Add the integration from Settings > Devices & Services > Add Integration.

## Lovelace search and download card

The repository includes a simple card for searching an ARR application and immediately starting its search/download workflow.

1. Copy `www/arr-media-manager-card.js` to your Home Assistant `config/www/` directory.
2. Add `/local/arr-media-manager-card.js` as a Lovelace resource of type `JavaScript module`.
3. Add the card to a dashboard and replace the config entry ID with the ID of the Sonarr, Radarr, or Lidarr entry you want to use.

```yaml
type: custom:arr-media-manager-card
title: ARR zoeken
config_entry_id: YOUR_CONFIG_ENTRY_ID
```

The selected config entry determines whether the request goes to Sonarr, Radarr, or Lidarr. The card sends `arr_media_manager.search_and_add` with `search_after_add: true`.

## Manual installation

Copy the folder

custom_components/arr_media_manager

into the following location on your Home Assistant system:

<config>/custom_components/arr_media_manager

Then restart Home Assistant and add the integration through the UI.

## Configuration

The integration is configured in the UI. Provide:

- Application type
- Instance name
- Base URL
- API key
- Verify SSL certificate
- Request timeout

The base URL is normalized and validated before the config entry is created.

## Reconfiguration

Use the integration's reconfigure flow to change connection or instance details. Invalid credentials can be refreshed through reauthentication.

## Available entities

- Application version
- Queue count
- Health issue count
- Free disk space
- Total disk space
- Used disk percentage
- Series/movie/artist counts and missing/wanted counts when supported
- Connected state
- Healthy state
- Queue active state
- Disk space low state
- Application-specific command buttons
- Default quality profile, root folder, and monitoring mode selectors

## Available actions

- arr_media_manager.lookup
- arr_media_manager.add_media
- arr_media_manager.search_and_add
- arr_media_manager.trigger_search
- arr_media_manager.refresh
- arr_media_manager.delete_media

## YAML action examples

```yaml
service: arr_media_manager.lookup
target:
  config_entry_id: 0123456789abcdef0123456789abcdef
data:
  query: "Blade Runner"
  max_results: 10
```

```yaml
service: arr_media_manager.add_media
target:
  config_entry_id: 0123456789abcdef0123456789abcdef
data:
  lookup_id: "tt0083658"
  root_folder: "/mnt/media/movies"
  quality_profile: "2160p Remux"
  monitoring_mode: "all"
  search_after_add: true
```

```yaml
service: arr_media_manager.search_and_add
target:
  config_entry_id: 0123456789abcdef0123456789abcdef
data:
  query: "The Expanse"
  year: 2015
  exact_match: true
  root_folder: "/mnt/media/series"
  quality_profile: "HD-1080p"
  monitoring_mode: "future"
  search_after_add: true
```

```yaml
service: arr_media_manager.trigger_search
target:
  config_entry_id: 0123456789abcdef0123456789abcdef
data:
  media_id: 123
  season_number: 1
```

```yaml
service: arr_media_manager.refresh
target:
  config_entry_id: 0123456789abcdef0123456789abcdef
data:
  action: "library"
```

```yaml
service: arr_media_manager.delete_media
target:
  config_entry_id: 0123456789abcdef0123456789abcdef
data:
  media_id: 123
  delete_files: false
  add_import_exclusion: false
  confirm: true
```

## Dashboard examples

A simple status dashboard can be built with standard Home Assistant cards:

- Entities card for status sensors
- Buttons card for RSS sync and refresh actions
- Markdown card for URL and application information
- Helper input_text for search terms
- Script to call `search_and_add`

Mushroom cards may be used for a more polished layout, but the base example does not require them.

## Security notes

- API keys are not logged.
- Diagnostics redact credentials and authorization data.
- Deletion is disabled unless explicitly confirmed.
- SSL verification is enabled by default.
- No remote proxy or public exposure is introduced.

## Troubleshooting

- Ensure the base URL points directly to the ARR web UI and not a reverse proxy.
- Verify the API key and permissions.
- Confirm the application selected in config matches the ARR instance.
- Check that SSL certificates are valid if verification is enabled.
- Inspect the integration logs for debug-level request diagnostics.

## Known limitations

- This integration communicates directly with the ARR APIs and does not create a separate middleware service.
- Some Lidarr operations vary by API version and are only exposed when they are safe to support.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
```

## Running tests

```bash
pytest -q
```

## Contribution guidance

Contributions are welcome. Please keep changes focused, maintain type annotations, update translation strings, and add tests for behavioral changes.

## License

This project is licensed under the MIT License.
