#!/usr/bin/env python3
"""
Helper for invoking the Playwright Lambda function.

Usage:
    # Inline script
    python examples/invoke.py --url https://example.com --script "result['title'] = page.title()"

    # Script from a local file
    python examples/invoke.py --url https://example.com --file examples/extract_links.py

    # Script from S3
    python examples/invoke.py --url https://example.com --s3 s3://bucket/scripts/scrape.py

    # Pass custom params
    python examples/invoke.py --url https://todomvc.com/examples/react/dist/ \\
        --file examples/todomvc_add_items.py \\
        --param todos='["Alpha","Bravo","Charlie"]'

    # Local Docker testing (no AWS credentials needed)
    python examples/invoke.py --local --url https://example.com --script "result['title'] = page.title()"
"""

import argparse
import json
import sys


def invoke_lambda(function_name, payload, region=None):
    import boto3

    client = boto3.client("lambda", region_name=region)
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    result = json.loads(response["Payload"].read())
    return result


def invoke_local(port, payload):
    import urllib.request

    url = f"http://localhost:{port}/2015-03-31/functions/function/invocations"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Invoke the Playwright Lambda function")
    parser.add_argument("--url", help="URL to navigate to before running script")
    parser.add_argument("--script", help="Inline Playwright script")
    parser.add_argument("--file", help="Path to a local .py script file")
    parser.add_argument("--s3", help="S3 URI to a script file (s3://bucket/key)")
    parser.add_argument("--param", action="append", default=[], help="Key=value params (repeatable)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--wait-until", default="load", choices=["load", "domcontentloaded", "networkidle"])
    parser.add_argument("--function", default="TheatreFunction", help="Lambda function name")
    parser.add_argument("--region", help="AWS region")
    parser.add_argument("--local", action="store_true", help="Invoke against local Docker container")
    parser.add_argument("--port", type=int, default=9000, help="Local Docker container port")
    args = parser.parse_args()

    if not args.script and not args.file and not args.s3:
        parser.error("Provide --script, --file, or --s3")

    payload = {"timeout": args.timeout, "wait_until": args.wait_until}

    if args.url:
        payload["url"] = args.url

    if args.file:
        with open(args.file) as f:
            payload["script"] = f.read()
    elif args.script:
        payload["script"] = args.script
    elif args.s3:
        payload["s3_uri"] = args.s3

    if args.param:
        params = {}
        for p in args.param:
            key, val = p.split("=", 1)
            try:
                params[key] = json.loads(val)
            except json.JSONDecodeError:
                params[key] = val
        payload["params"] = params

    if args.local:
        result = invoke_local(args.port, payload)
    else:
        result = invoke_lambda(args.function, payload, args.region)

    if isinstance(result, dict) and "body" in result:
        try:
            body = json.loads(result["body"])
            print(json.dumps(body, indent=2))
        except (json.JSONDecodeError, TypeError):
            print(result["body"])
        if result.get("statusCode", 200) >= 400:
            sys.exit(1)
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
