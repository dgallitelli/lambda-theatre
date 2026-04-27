# Take a full-page screenshot and upload to S3.
# NOTE: Requires s3:PutObject permission. The default SAM template only grants
#       s3:GetObject for script loading. Add an S3CrudPolicy or a custom IAM
#       statement to your Lambda role before using this example.
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
