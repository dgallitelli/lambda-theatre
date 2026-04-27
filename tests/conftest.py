import sys
import os
import subprocess
import time
import json
import urllib.request

import pytest

CONTAINER_NAME = "lambda-theatre-ci"
PORT = 9000
BASE_URL = f"http://localhost:{PORT}/2015-03-31/functions/function/invocations"


def invoke(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


@pytest.fixture(scope="session")
def container():
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True,
    )
    subprocess.run(
        ["docker", "build", "-t", "lambda-theatre", "src/"],
        check=True,
        capture_output=True,
    )
    proc = subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{PORT}:8080",
            "lambda-theatre",
        ],
        check=True,
        capture_output=True,
    )

    for _ in range(30):
        try:
            invoke({"script": "pass"})
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Container did not become ready in 30s")

    yield invoke

    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
