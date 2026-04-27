import json
import subprocess
import time
import urllib.request

import pytest

CHROMIUM_CONTAINER = "lambda-theatre-ci"
LIGHTPANDA_CONTAINER = "lambda-theatre-lp-ci"
CHROMIUM_PORT = 9000
LIGHTPANDA_PORT = 9001


def make_invoker(port):
    base_url = f"http://localhost:{port}/2015-03-31/functions/function/invocations"

    def invoke(payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(base_url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    return invoke


def start_container(image, name, port, dockerfile=None, max_wait=60):
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    build_cmd = ["docker", "build", "-t", image]
    if dockerfile:
        build_cmd += ["-f", dockerfile]
    build_cmd.append("src/")
    subprocess.run(build_cmd, check=True, capture_output=True)
    subprocess.run(
        ["docker", "run", "-d", "--name", name, "-p", f"{port}:8080", image],
        check=True,
        capture_output=True,
    )
    invoke = make_invoker(port)
    for _ in range(max_wait):
        try:
            invoke({"script": "pass"})
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError(f"Container {name} did not become ready in {max_wait}s")
    return invoke


@pytest.fixture(scope="session")
def container():
    invoke = start_container("lambda-theatre", CHROMIUM_CONTAINER, CHROMIUM_PORT)
    yield invoke
    subprocess.run(["docker", "rm", "-f", CHROMIUM_CONTAINER], capture_output=True)


@pytest.fixture(scope="session")
def lightpanda_container():
    invoke = start_container(
        "lambda-theatre-lightpanda",
        LIGHTPANDA_CONTAINER,
        LIGHTPANDA_PORT,
        dockerfile="src/Dockerfile.lightpanda",
        max_wait=90,
    )
    yield invoke
    subprocess.run(["docker", "rm", "-f", LIGHTPANDA_CONTAINER], capture_output=True)
