"""
Unit tests for the invoke.py CLI helper.
These test argument parsing only — no Docker or AWS needed.
"""

import subprocess
import sys

INVOKE = "examples/invoke.py"


def run_invoke(*args):
    result = subprocess.run(
        [sys.executable, INVOKE, *args],
        capture_output=True,
        text=True,
    )
    return result


class TestArgValidation:
    def test_no_source_fails(self):
        r = run_invoke("--url", "https://example.com")
        assert r.returncode != 0
        assert "script" in r.stderr.lower() or "s3" in r.stderr.lower()

    def test_script_and_file_mutual_exclusion(self):
        r = run_invoke(
            "--script", "pass",
            "--file", "examples/extract_links.py",
        )
        assert r.returncode != 0
        assert "only one" in r.stderr.lower()

    def test_script_and_s3_mutual_exclusion(self):
        r = run_invoke(
            "--script", "pass",
            "--s3", "s3://bucket/key.py",
        )
        assert r.returncode != 0
        assert "only one" in r.stderr.lower()

    def test_file_and_s3_mutual_exclusion(self):
        r = run_invoke(
            "--file", "examples/extract_links.py",
            "--s3", "s3://bucket/key.py",
        )
        assert r.returncode != 0
        assert "only one" in r.stderr.lower()

    def test_all_three_mutual_exclusion(self):
        r = run_invoke(
            "--script", "pass",
            "--file", "examples/extract_links.py",
            "--s3", "s3://bucket/key.py",
        )
        assert r.returncode != 0
        assert "only one" in r.stderr.lower()
