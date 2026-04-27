"""
Playwright + Chromium runtime for AWS Lambda.

Chromium launches at module level (Lambda init phase -- free, not billed).
On warm starts the browser is already running; only a new page is created.

Accepts a Playwright script via:
  1. event["script"]  -- inline Python code (string)
  2. event["s3_uri"]  -- S3 path to a .py file (s3://bucket/scripts/scrape.py)

The script receives these pre-bound variables:
  - page      Playwright Page (navigated to event["url"] if provided)
  - browser   Playwright Browser instance (persistent across warm starts)
  - context   Playwright BrowserContext (fresh per invocation)
  - event     the full Lambda event dict
  - result    dict -- put your return data here

Optional event fields:
  - url           navigate before running script
  - wait_until    "load" | "domcontentloaded" | "networkidle" (default: "load")
  - timeout       seconds (default: 30)
  - viewport      {width, height} (default: 1280x720)
  - user_agent    custom User-Agent string
"""

import json
import traceback
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
    "--metrics-recording-only",
    "--mute-audio",
    "--font-render-hinting=none",
    "--disk-cache-dir=/tmp/chrome-cache",
]

# --- Init phase: launch browser ONCE (free, not billed) ---
_pw = sync_playwright().start()
_browser = _pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)


def _ensure_browser():
    global _browser
    try:
        if _browser and _browser.is_connected():
            _browser.contexts
            return
    except Exception:
        pass
    _browser = _pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)


def _fetch_script_from_s3(s3_uri):
    import boto3

    parts = s3_uri.replace("s3://", "").split("/", 1)
    bucket, key = parts[0], parts[1]
    s3 = boto3.client("s3")
    resp = s3.get_object(Bucket=bucket, Key=key)
    return resp["Body"].read().decode("utf-8")


def handler(event, context):
    _ensure_browser()

    script = event.get("script")
    s3_uri = event.get("s3_uri")

    if not script and not s3_uri:
        return {"statusCode": 400, "body": "Provide 'script' (inline) or 's3_uri'"}

    if s3_uri and not script:
        try:
            script = _fetch_script_from_s3(s3_uri)
        except Exception as e:
            return {"statusCode": 502, "body": f"Failed to fetch from S3: {e}"}

    url = event.get("url")
    timeout_ms = event.get("timeout", 30) * 1000

    ctx = None
    page = None
    try:
        ctx = _browser.new_context(
            viewport=event.get("viewport", {"width": 1280, "height": 720}),
            user_agent=event.get("user_agent"),
        )
        page = ctx.new_page()
        page.set_default_timeout(timeout_ms)
        page.set_default_navigation_timeout(timeout_ms)

        if url:
            page.goto(url, wait_until=event.get("wait_until", "load"))

        result = {}

        exec(script, {
            "page": page,
            "browser": _browser,
            "context": ctx,
            "event": event,
            "result": result,
            "json": json,
        })

        return {"statusCode": 200, "body": json.dumps(result, default=str)}

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": type(e).__name__,
                "message": str(e),
                "trace": traceback.format_exc().split("\n")[-4:],
            }),
        }
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
