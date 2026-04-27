"""
Unit tests for handler input validation and warmup logic.
Run against the container via the Lambda RIE.
"""

import pytest


class TestWarmup:
    def test_empty_event_returns_200(self, container):
        r = container({})
        assert r["statusCode"] == 200
        assert r["body"] == "warm"

    def test_none_fields_returns_200(self, container):
        r = container({"script": None, "s3_uri": None})
        assert r["statusCode"] == 200


class TestInputValidation:
    def test_invalid_timeout_string(self, container):
        r = container({"script": "pass", "timeout": "slow"})
        assert r["statusCode"] == 400
        assert "timeout" in r["body"].lower()

    def test_invalid_timeout_null(self, container):
        r = container({"script": "pass", "timeout": None})
        assert r["statusCode"] == 400

    def test_invalid_viewport_string(self, container):
        r = container({"script": "pass", "viewport": "1280x720"})
        assert r["statusCode"] == 400
        assert "viewport" in r["body"].lower()

    def test_invalid_viewport_missing_keys(self, container):
        r = container({"script": "pass", "viewport": {"width": 1280}})
        assert r["statusCode"] == 400

    def test_invalid_wait_until(self, container):
        r = container({"script": "pass", "wait_until": "loaded"})
        assert r["statusCode"] == 400
        assert "wait_until" in r["body"].lower()

    def test_valid_wait_until_values(self, container):
        for val in ["load", "domcontentloaded", "networkidle", "commit"]:
            r = container({
                "url": "https://example.com",
                "script": "result['ok'] = True",
                "wait_until": val,
            })
            assert r["statusCode"] == 200, f"Failed for wait_until={val}"

    def test_invalid_s3_uri_format(self, container):
        r = container({"s3_uri": "not-an-s3-uri"})
        assert r["statusCode"] == 502
        assert "Invalid S3 URI" in r["body"]

    def test_invalid_s3_uri_no_key(self, container):
        r = container({"s3_uri": "s3://bucket-only"})
        assert r["statusCode"] == 502


class TestScriptPrecedence:
    def test_script_wins_over_s3(self, container):
        r = container({
            "script": "result['source'] = 'inline'",
            "s3_uri": "s3://nonexistent/script.py",
        })
        assert r["statusCode"] == 200
        import json
        body = json.loads(r["body"])
        assert body["source"] == "inline"
