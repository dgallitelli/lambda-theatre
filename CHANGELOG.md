# Changelog

## 0.2.0 (2026-04-27)

- Add Lightpanda as a second browser backend (`"browser": "lightpanda"`)
- New `Dockerfile.lightpanda` for lightweight image (~450 MB vs ~1.2 GB)
- Handler auto-detects available backend at init
- New Makefile targets: `build-lightpanda`, `test-lightpanda`, `test-all-lightpanda`
- Lightpanda integration tests (navigation, SPA, params, errors, consecutive invocations)

## 0.1.0 (2026-04-27)

Initial release.

- Playwright + Chromium on Ubuntu 25.04 container image (Python 3.13, GLIBC 2.41)
- Module-level browser launch (Lambda free init phase)
- Script injection via event payload or S3
- Optimized Chromium flags for Lambda
- SAM template for one-command deploy (no public endpoints)
- 6 example scripts: link extraction, form fill, SPA interaction, screenshot to S3, dynamic content extraction, multi-page HN scraper
- Local testing via Lambda Runtime Interface Emulator
