"""
Playwright browser automation runtime for AWS Lambda.

Supports two browser backends:
  - Chromium (via Playwright, default) — full browser, larger image
  - Lightpanda (via CDP) — lightweight, faster, smaller image

The handler auto-detects which backend is available based on what's installed
in the container image. The event field "browser" can request a specific backend.

Accepts a Playwright script via:
  1. event["script"]  -- inline Python code (string)
  2. event["s3_uri"]  -- S3 path to a .py file (s3://bucket/scripts/scrape.py)

If both are provided, "script" takes precedence.

The script receives these pre-bound variables:
  - page      Playwright Page (navigated to event["url"] if provided)
  - browser   Playwright Browser instance (persistent across warm starts)
  - context   Playwright BrowserContext (fresh per invocation)
  - event     the full Lambda event dict
  - result    dict -- put your return data here

Standard imports (import boto3, import time, etc.) work normally in scripts.

Optional event fields:
  - browser       "chromium" | "lightpanda" (default: auto-detect)
  - url           navigate before running script
  - wait_until    "load" | "domcontentloaded" | "networkidle" | "commit" (default: "load")
  - timeout       seconds (default: 30)
  - viewport      {width, height} (default: 1280x720, Chromium only)
  - user_agent    custom User-Agent string
"""

import json
import os
import pathlib
import shutil
import subprocess
import time as _time
import traceback
import urllib.request

from playwright.sync_api import sync_playwright

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-zygote",
    "--no-first-run",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--disable-component-update",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--disable-ipc-flooding-protection",
    "--disable-features=PaintHolding",
    "--metrics-recording-only",
    "--mute-audio",
    "--font-render-hinting=none",
    "--disk-cache-dir=/tmp/chrome-cache",
]

_VALID_WAIT_UNTIL = {"load", "domcontentloaded", "networkidle", "commit"}
_VALID_BROWSERS = {"chromium", "lightpanda"}
_DEBUG = os.environ.get("PLAYWRIGHT_DEBUG", "").lower() in ("1", "true")
_LIGHTPANDA_PORT = 9333

# --- Detect available backends ---
_pw = sync_playwright().start()

_CHROMIUM_AVAILABLE = bool(
    os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    and any(
        pathlib.Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"]).glob("chromium-*/chrome-linux*/chrome")
    )
)
_LIGHTPANDA_AVAILABLE = bool(shutil.which("lightpanda"))

# --- Launch available backend at init (free phase) ---
_chromium_browser = None
_lp_browser = None
_lp_proc = None

if _CHROMIUM_AVAILABLE:
    _chromium_browser = _pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)

if _LIGHTPANDA_AVAILABLE:
    _lp_proc = subprocess.Popen(
        ["lightpanda", "serve", "--host", "127.0.0.1", "--port", str(_LIGHTPANDA_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{_LIGHTPANDA_PORT}/json/version", timeout=1
            )
            break
        except Exception:
            _time.sleep(0.2)
    _lp_browser = _pw.chromium.connect_over_cdp(f"http://127.0.0.1:{_LIGHTPANDA_PORT}")


def _ensure_chromium():
    global _chromium_browser
    try:
        if _chromium_browser and _chromium_browser.is_connected():
            _chromium_browser.contexts
            return
    except Exception:
        pass
    _chromium_browser = _pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)


def _ensure_lightpanda():
    global _lp_browser, _lp_proc
    try:
        if _lp_proc and _lp_proc.poll() is None and _lp_browser and _lp_browser.is_connected():
            return
    except Exception:
        pass
    if _lp_proc:
        try:
            _lp_proc.kill()
        except Exception:
            pass
    _lp_proc = subprocess.Popen(
        ["lightpanda", "serve", "--host", "127.0.0.1", "--port", str(_LIGHTPANDA_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(30):
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{_LIGHTPANDA_PORT}/json/version", timeout=1
            )
            break
        except Exception:
            _time.sleep(0.2)
    _lp_browser = _pw.chromium.connect_over_cdp(f"http://127.0.0.1:{_LIGHTPANDA_PORT}")


def _fetch_script_from_s3(s3_uri):
    import boto3

    if not s3_uri.startswith("s3://") or "/" not in s3_uri[5:]:
        raise ValueError(f"Invalid S3 URI: {s3_uri}. Expected s3://bucket/key")
    parts = s3_uri[5:].split("/", 1)
    bucket, key = parts[0], parts[1]
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read().decode("utf-8")


def handler(event, context):
    if not event or (not event.get("script") and not event.get("s3_uri")):
        return {"statusCode": 200, "body": "warm"}

    # --- Validate and resolve browser backend ---
    requested = event.get("browser")
    if requested is not None and requested not in _VALID_BROWSERS:
        return {
            "statusCode": 400,
            "body": f"Field 'browser' must be one of {sorted(_VALID_BROWSERS)}",
        }

    if requested == "chromium" and not _CHROMIUM_AVAILABLE:
        return {"statusCode": 400, "body": "Browser 'chromium' is not available in this image"}
    if requested == "lightpanda" and not _LIGHTPANDA_AVAILABLE:
        return {"statusCode": 400, "body": "Browser 'lightpanda' is not available in this image"}

    if requested:
        use_backend = requested
    elif _CHROMIUM_AVAILABLE:
        use_backend = "chromium"
    elif _LIGHTPANDA_AVAILABLE:
        use_backend = "lightpanda"
    else:
        return {"statusCode": 500, "body": "No browser backend available"}

    if use_backend == "chromium":
        _ensure_chromium()
        active_browser = _chromium_browser
    else:
        _ensure_lightpanda()
        active_browser = _lp_browser

    # --- Validate inputs ---
    script = event.get("script")
    s3_uri = event.get("s3_uri")

    if s3_uri and not script:
        try:
            script = _fetch_script_from_s3(s3_uri)
        except Exception as e:
            return {"statusCode": 502, "body": f"Failed to fetch from S3: {e}"}

    url = event.get("url")
    try:
        timeout_ms = int(event.get("timeout", 30)) * 1000
    except (TypeError, ValueError):
        return {"statusCode": 400, "body": "Field 'timeout' must be a number (seconds)"}

    viewport = event.get("viewport", {"width": 1280, "height": 720})
    if not isinstance(viewport, dict) or "width" not in viewport or "height" not in viewport:
        return {
            "statusCode": 400,
            "body": 'Field \'viewport\' must be {"width": int, "height": int}',
        }

    wait_until = event.get("wait_until", "load")
    if wait_until not in _VALID_WAIT_UNTIL:
        return {
            "statusCode": 400,
            "body": f"Field 'wait_until' must be one of {sorted(_VALID_WAIT_UNTIL)}",
        }

    ctx = None
    page = None
    try:
        context_kwargs = {}
        if use_backend == "chromium":
            context_kwargs["viewport"] = viewport
        if event.get("user_agent"):
            context_kwargs["user_agent"] = event["user_agent"]

        ctx = active_browser.new_context(**context_kwargs)
        page = ctx.new_page()
        page.set_default_timeout(timeout_ms)
        page.set_default_navigation_timeout(timeout_ms)

        if url:
            goto_kwargs = {}
            if use_backend == "chromium":
                goto_kwargs["wait_until"] = wait_until
            page.goto(url, **goto_kwargs)

        result = {}

        exec(
            script,
            {
                "__name__": "__script__",
                "page": page,
                "browser": active_browser,
                "context": ctx,
                "event": event,
                "result": result,
                "json": json,
            },
        )

        return {"statusCode": 200, "body": json.dumps(result, default=str)}

    except Exception as e:
        body = {"error": type(e).__name__, "message": str(e)}
        if _DEBUG:
            body["trace"] = traceback.format_exc().split("\n")[-4:]
        return {"statusCode": 500, "body": json.dumps(body)}
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass
        if ctx:
            try:
                ctx.close()
            except Exception:
                pass
