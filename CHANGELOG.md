# Changelog

## 0.1.0 (2026-04-27)

Initial release.

- Playwright + Chromium on Ubuntu 24.04 container image
- Module-level browser launch (Lambda free init phase)
- Script injection via event payload or S3
- Optimized Chromium flags for Lambda
- SAM template for one-command deploy (no public endpoints)
- 6 example scripts: link extraction, form fill, SPA interaction, screenshot to S3, dynamic content extraction, multi-page HN scraper
- Local testing via Lambda Runtime Interface Emulator
