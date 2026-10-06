# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-06

### Added

- Initial release: async Skylight Calendar API client extracted from the
  `skylight` Home Assistant integration.
- OAuth2 authorization code + PKCE helpers (`pkce_pair`, `authorize_url`,
  `extract_code`) and token exchanges (`exchange_authorization_code`,
  `exchange_refresh_token`).
- `SkylightAPI` client: frames, devices (incl. Skylight Buddy alarms),
  calendar events CRUD, source calendars, categories, lists & list items,
  chores (fan-out create, complete/uncomplete, delete), meals & recipes,
  rewards, task box, photo feeds.
- Automatic 401 → refresh-token → retry cascade with a
  `token_update_cb` persistence callback.
- Opt-in ETag caching on the GETs the Skylight web app validates
  (frames, categories, devices, source calendars, avatars, colors).
- `upload_media`: short-lived S3 credentials → AWS SigV4-signed PUT →
  upload registration.
- Typed throughout (`py.typed`, mypy strict clean).
