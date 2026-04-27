# aws-lambda-chromium-playwright-python

Container image for running Playwright + Chromium on AWS Lambda. Build the image once, inject Playwright scripts at runtime via the event payload or S3.

## How it works

The container image ships Chromium and Playwright pre-installed on Ubuntu 24.04. At Lambda cold start, Chromium launches during the **free init phase** (not billed). Your Playwright script runs against the already-warm browser, then the page and context are cleaned up. On warm starts, the browser is reused — only a new page is created.

```
[Your script] --> Lambda handler --> Playwright --> Chromium (pre-launched)
                    |
                    +-- inline via event["script"]
                    +-- from S3 via event["s3_uri"]
```

## Performance

Measured locally via Lambda Runtime Interface Emulator:

| Metric | Time |
|--------|------|
| Cold start (first invocation) | ~850ms |
| Warm start (simple page) | ~70ms |
| Warm start (React SPA interaction) | ~300ms |

Chromium launches during Lambda's free init phase. The handler only pays for page creation + navigation + script execution.

## Quick start

### Build and test locally

```bash
make build
make test
```

Or manually:

```bash
docker build -t playwright-lambda .
docker run -d --name test -p 9000:8080 playwright-lambda
sleep 3

# Get a page title
curl -s -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"url": "https://example.com", "script": "result[\"title\"] = page.title()"}' \
  | python3 -m json.tool

docker rm -f test
```

### Deploy to AWS

```bash
sam build && sam deploy --guided --stack-name playwright-lambda
```

### Invoke

```bash
aws lambda invoke \
  --function-name PlaywrightFunction \
  --cli-binary-format raw-in-base64-out \
  --payload '{"url": "https://example.com", "script": "result[\"title\"] = page.title()"}' \
  /dev/stdout | python3 -m json.tool
```

Or with the included helper:

```bash
python3 example_invoke.py --url https://example.com --script "result['title'] = page.title()"
```

## Event schema

```json
{
  "url": "https://example.com",
  "script": "result['title'] = page.title()",
  "s3_uri": "s3://my-bucket/scripts/scrape.py",
  "timeout": 30,
  "wait_until": "load",
  "viewport": {"width": 1280, "height": 720},
  "user_agent": "custom-agent/1.0",
  "params": {"any": "data your script needs"}
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `script` | One of `script` or `s3_uri` | Inline Python code |
| `s3_uri` | One of `script` or `s3_uri` | S3 path to a `.py` script file |
| `url` | No | Navigate to this URL before running the script |
| `timeout` | No | Timeout in seconds (default: 30) |
| `wait_until` | No | `load` \| `domcontentloaded` \| `networkidle` (default: `load`) |
| `viewport` | No | `{width, height}` (default: 1280x720) |
| `user_agent` | No | Custom User-Agent string |
| `params` | No | Arbitrary data accessible as `event["params"]` in your script |

## Script environment

Your script receives these variables — no imports needed:

| Variable | Type | Description |
|----------|------|-------------|
| `page` | `playwright.sync_api.Page` | Already navigated to `event["url"]` if provided |
| `browser` | `playwright.sync_api.Browser` | Persistent across warm starts |
| `context` | `playwright.sync_api.BrowserContext` | Fresh per invocation |
| `event` | `dict` | Full Lambda event (access `event["params"]`, etc.) |
| `result` | `dict` | Put your return data here |
| `json` | `module` | The `json` module, pre-imported |

## Examples

### Extract text from a page

```python
# Inline
{"url": "https://example.com", "script": "result['text'] = page.inner_text('body')"}
```

### Interact with a React SPA

```python
{
  "url": "https://todomvc.com/examples/react/dist/",
  "script": "page.wait_for_selector('input.new-todo')\nfor item in event['params']['todos']:\n    page.fill('input.new-todo', item)\n    page.press('input.new-todo', 'Enter')\nresult['count'] = page.locator('ul.todo-list li').count()",
  "params": {"todos": ["Buy milk", "Write tests", "Ship it"]}
}
```

### Fill a form and submit

```python
{
  "url": "https://httpbin.org/forms/post",
  "script": "page.fill('input[name=\"custname\"]', 'Lambda Bot')\npage.fill('input[name=\"custemail\"]', 'bot@example.com')\npage.click('button[type=\"submit\"]')\npage.wait_for_load_state('load')\nresult['url'] = page.url"
}
```

### Load script from S3

```python
{"url": "https://example.com", "s3_uri": "s3://my-bucket/scripts/extract.py"}
```

The Lambda function needs `s3:GetObject` permission on the bucket. The SAM template handles this automatically — pass the bucket name at deploy time:

```bash
sam deploy --parameter-overrides ScriptBucket=my-bucket
```

Or add the permission manually if deploying outside SAM:

```json
{
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/scripts/*"
}
```

See the [`examples/`](examples/) directory for more complete examples and a Python invocation helper.

## Why container image?

Lambda zip deployments have a 250 MB unzipped limit. Chromium alone is ~300 MB. Container images support up to 10 GB, and Lambda caches them across invocations.

Ubuntu 24.04 is used because Playwright's Chromium requires GLIBC 2.39+, which Amazon Linux 2023 does not ship.

## Cold start optimization

This image applies several techniques to minimize cold start latency:

1. **Module-level browser launch** — Chromium starts during Lambda's free init phase (not billed)
2. **Optimized Chromium flags** — 15+ flags disable unnecessary features (extensions, sync, translate, background networking, component updates)
3. **Disk cache in /tmp** — V8 compiled code and resources persist across warm invocations
4. **Layer ordering** — Dockerfile layers ordered by change frequency (OS first, handler code last)
5. **Stripped locales and docs** — unnecessary Chromium files removed from image

### Keeping the function warm

To avoid cold starts during normal traffic, add a scheduled warmup ping:

```bash
aws events put-rule --name playwright-warmup --schedule-expression "rate(5 minutes)"
```

The handler detects empty events and returns immediately (~100ms), keeping the execution environment alive.

**Cost comparison (2048 MB, keeping 1 instance warm):**

| Strategy | Monthly cost | Guarantee |
|----------|-------------|-----------|
| EventBridge warmup (5 min) | ~$0.07 | Best-effort (Lambda may occasionally recycle the environment) |
| Provisioned concurrency = 1 | ~$21.60 | Guaranteed always-warm |

The warmup approach is **300x cheaper** and works well in practice — Lambda rarely recycles environments that are pinged every 5 minutes. Use provisioned concurrency only when you need a hard SLA on response latency.

## Security

- **No public endpoints.** The SAM template creates a Lambda function with no Function URL, no API Gateway, and no public access. Invoke via SDK or CLI only.
- **Chromium binds to localhost.** No network ports are exposed.
- **Script injection.** The handler runs arbitrary Python code from the event payload. In production, validate or restrict the `script` field at the API layer (e.g., API Gateway request validation) or use `s3_uri` to load only pre-approved scripts.

## Project structure

```
Dockerfile          Container image (Ubuntu 24.04 + Chromium + Playwright + Lambda RIE)
handler.py          Lambda handler (script injection runtime)
entry.sh            Bootstrap (Lambda RIE for local, awslambdaric for deployed)
requirements.txt    Python dependencies
template.yaml       SAM template (one function, no public access)
Makefile            build / test / deploy shortcuts
example_invoke.py   Python helper for invoking the function
examples/           Example Playwright scripts for common use cases
ARCHITECTURE.md     Integration patterns (API Gateway, Step Functions)
```

## Requirements

- Docker
- AWS SAM CLI (for deployment)
- Python 3.12+ (for local invocation helper)
- AWS credentials configured

## License

MIT
