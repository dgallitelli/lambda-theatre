# Take a full-page screenshot and upload to S3.
# Usage: {"url": "https://example.com", "params": {"bucket": "my-bucket", "key": "screenshots/example.png"}}

import boto3
import base64

buf = page.screenshot(full_page=True)

bucket = event["params"]["bucket"]
key = event["params"]["key"]

s3 = boto3.client("s3")
s3.put_object(Bucket=bucket, Key=key, Body=buf, ContentType="image/png")

result["s3_uri"] = f"s3://{bucket}/{key}"
result["size_bytes"] = len(buf)
