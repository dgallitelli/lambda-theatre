# Design: Lightpanda Browser Backend

## Summary

Add Lightpanda as a second browser backend alongside Chromium. Each backend ships in its own container image. A shared `handler.py` auto-detects which backend is installed and routes accordingly. Sideloaded Python scripts remain unchanged.

## Motivation

Lightpanda is a Zig-based headless browser that speaks CDP. Benchmarks against the current Chromium/Playwright stack show:

- 63% smaller container image (423 MB vs 1,135 MB)
- Faster warm execution on most pages (2-4x on light pages, comparable on JS-heavy ones)
- Correct results on all tested government and SPA pages

Trade-off: incomplete CDP compatibility (fails on navigation-heavy pages like Wikipedia) and slower on extremely JS-heavy pages where V8's JIT dominates.

## Event API

New optional field `browser`:

```json
{
  "browser": "lightpanda",
  "url": "https://example.com",
  "script": "result['title'] = page.title()"
}
```

| Field | Type | Default | Values |
|-------|------|---------|--------|
| `browser` | string | auto-detected from image | `"chromium"`, `"lightpanda"` |

- If omitted, uses whichever backend is available in the image.
- If the requested backend is not installed in the image, returns 400: `"Browser '<name>' is not available in this image"`.
- If both are somehow installed (e.g. local dev), `"chromium"` is the default.
- All other event fields are unchanged.

## handler.py Changes

### Module-level init

Auto-detect available backends and eagerly launch whichever is present:

```
_pw = sync_playwright().start()

_CHROMIUM_AVAILABLE: detected by checking PLAYWRIGHT_BROWSERS_PATH for chromium
_LIGHTPANDA_AVAILABLE: detected by shutil.which("lightpanda")

if _CHROMIUM_AVAILABLE:
    _chromium_browser = launch chromium with CHROMIUM_ARGS (same as today)
if _LIGHTPANDA_AVAILABLE:
    _lp_proc = start lightpanda subprocess ("lightpanda serve --host 127.0.0.1 --port 9333")
    wait for CDP endpoint to be ready
    _lp_browser = _pw.chromium.connect_over_cdp("http://127.0.0.1:9333")
```

### _ensure_lightpanda()

Mirrors existing `_ensure_browser()` pattern:
1. Check if `_lp_proc` is alive (poll() is None)
2. Check if `_lp_browser.is_connected()`
3. If either fails: kill old process, restart subprocess, reconnect via CDP

### handler() changes

```
requested = event.get("browser")

if requested and requested not in ("chromium", "lightpanda"):
    return 400

resolve actual backend:
    if requested: use it (error if unavailable)
    elif _CHROMIUM_AVAILABLE: use chromium
    elif _LIGHTPANDA_AVAILABLE: use lightpanda
    else: return 500 "no browser available"

ensure the selected backend is healthy

create context and page from the selected browser object
```

### Lightpanda-specific handling

- Skip `viewport` kwarg in `new_context()` — Lightpanda does not support it.
- Skip `wait_until` kwarg in `page.goto()` — pass only URL.
- Everything else (script exec, result dict, cleanup) is identical.

### Global state

Current:
- `_pw`, `_browser` (Chromium)

New:
- `_pw` (shared)
- `_chromium_browser`, `_ensure_chromium()` (renamed from `_browser`, `_ensure_browser()`)
- `_lp_proc`, `_lp_browser`, `_ensure_lightpanda()`

## Dockerfile (existing, unchanged)

`src/Dockerfile` — Chromium-only image. No modifications. Existing deployments unaffected.

## Dockerfile.lightpanda (new)

`src/Dockerfile.lightpanda`:

```
FROM ubuntu:25.04

Layer 1: OS packages
    python3, python3-pip, curl, ca-certificates

Layer 2: Playwright Python package + boto3 (NO browser install)
    pip install playwright boto3
    (no "playwright install chromium" — just the CDP client library)

Layer 3: Lightpanda binary
    curl from github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-x86_64-linux
    -> /usr/local/bin/lightpanda

Layer 4: Lambda runtime (awslambdaric + RIE)

Layer 5: entry.sh + handler.py
```

Reuses same `entry.sh`, same `handler.py`, same `CMD ["handler.handler"]`.

Expected image size: ~450-500 MB.

## Makefile Changes

New targets:

```makefile
build-lightpanda:
    docker build -t lambda-theatre-lightpanda -f src/Dockerfile.lightpanda src/

test-lightpanda: build-lightpanda
    (same pattern as existing test target, using lambda-theatre-lightpanda image)
```

## Test Changes

### test_handler_unit.py

New tests:
- `"browser": "invalid"` returns 400
- `"browser": ""` returns 400
- Warmup event (empty) still returns `{"statusCode": 200, "body": "warm"}` regardless of backend

### test_handler_integration.py

Add Lightpanda integration tests that mirror key Chromium tests:
- Basic navigation (page title)
- TodoMVC React SPA (fill, interact, extract)
- JS evaluation
- Script with params
- Error handling (syntax error, timeout)

These run against the Lightpanda image via a separate conftest fixture or a parametrized container fixture.

Do NOT use any government site URLs in tests. Use: example.com, todomvc.com, httpbin.org, quotes.toscrape.com.

## Documentation Changes

### README.md

- Add `browser` to the event schema table
- Add a "Browser Backends" section explaining Chromium vs Lightpanda trade-offs
- Add `make build-lightpanda` to the build instructions
- Add a Lightpanda example invocation

### ARCHITECTURE.md

- Update the handler flow to show backend selection step
- Add Lightpanda to the component diagram

### CHANGELOG.md

- New feature entry for Lightpanda backend support

## Out of Scope

- ARM64 / Graviton Lightpanda build (only x86_64 nightly available)
- SAM template changes (user can add a second function manually)
- Bundling both browsers in one image (rejected — negates image size advantage)
- Automated fallback from Lightpanda to Chromium on failure
