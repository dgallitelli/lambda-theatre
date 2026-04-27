"""
Integration tests — run real Playwright scripts against live sites.
Requires Docker + internet access.
"""

import json


class TestBasicNavigation:
    def test_page_title(self, container):
        r = container(
            {
                "url": "https://example.com",
                "script": "result['title'] = page.title()",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["title"] == "Example Domain"

    def test_page_content(self, container):
        r = container(
            {
                "url": "https://example.com",
                "script": "result['html'] = page.content()[:100]",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert "<html" in body["html"].lower()

    def test_evaluate_js(self, container):
        r = container(
            {
                "url": "https://example.com",
                "script": "result['links'] = page.evaluate('document.querySelectorAll(\"a\").length')",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert isinstance(body["links"], (int, float))


class TestInteraction:
    def test_todomvc_fill_and_enter(self, container):
        r = container(
            {
                "url": "https://todomvc.com/examples/react/dist/",
                "script": (
                    "page.wait_for_selector('input.new-todo')\n"
                    "page.fill('input.new-todo', 'Test item')\n"
                    "page.press('input.new-todo', 'Enter')\n"
                    "result['count'] = page.locator('ul.todo-list li').count()"
                ),
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["count"] == 1

    def test_multi_step_with_params(self, container):
        r = container(
            {
                "url": "https://example.com",
                "params": {"selectors": ["h1", "p", "a"]},
                "script": (
                    "result['texts'] = []\n"
                    "for sel in event['params']['selectors']:\n"
                    "    el = page.query_selector(sel)\n"
                    "    if el:\n"
                    "        result['texts'].append(el.inner_text())\n"
                ),
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert len(body["texts"]) == 3
        assert "Example Domain" in body["texts"][0]


class TestScriptImports:
    def test_import_time(self, container):
        r = container(
            {
                "script": "import time; result['ts'] = int(time.time())",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["ts"] > 0

    def test_import_json_builtin(self, container):
        r = container(
            {
                "script": "result['parsed'] = json.loads('{\"a\": 1}')",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["parsed"] == {"a": 1}


class TestParams:
    def test_event_params_passed_to_script(self, container):
        r = container(
            {
                "script": "result['greeting'] = f\"Hello {event['params']['name']}\"",
                "params": {"name": "Lambda"},
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["greeting"] == "Hello Lambda"


class TestErrorHandling:
    def test_script_syntax_error(self, container):
        r = container(
            {
                "script": "def broken(",
            }
        )
        assert r["statusCode"] == 500
        body = json.loads(r["body"])
        assert body["error"] == "SyntaxError"

    def test_script_runtime_error(self, container):
        r = container(
            {
                "script": "x = 1 / 0",
            }
        )
        assert r["statusCode"] == 500
        body = json.loads(r["body"])
        assert body["error"] == "ZeroDivisionError"

    def test_navigation_timeout(self, container):
        r = container(
            {
                "url": "https://httpbin.org/delay/10",
                "script": "result['ok'] = True",
                "timeout": 3,
            }
        )
        assert r["statusCode"] == 500
        body = json.loads(r["body"])
        assert "Timeout" in body["error"] or "timeout" in body["message"].lower()

    def test_selector_timeout(self, container):
        r = container(
            {
                "url": "https://example.com",
                "script": "page.wait_for_selector('#nonexistent', timeout=2000)",
            }
        )
        assert r["statusCode"] == 500
        body = json.loads(r["body"])
        assert "Timeout" in body["error"]


class TestCustomOptions:
    def test_custom_viewport(self, container):
        r = container(
            {
                "url": "https://example.com",
                "script": "result['width'] = page.evaluate('window.innerWidth')",
                "viewport": {"width": 375, "height": 812},
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["width"] == 375

    def test_custom_user_agent(self, container):
        r = container(
            {
                "url": "https://httpbin.org/user-agent",
                "script": "result['ua'] = page.evaluate('document.body.innerText')",
                "user_agent": "LambdaTheatre/1.0",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert "LambdaTheatre/1.0" in body["ua"]


class TestConsecutiveInvocations:
    def test_browser_survives_multiple_invocations(self, container):
        for i in range(5):
            r = container(
                {
                    "url": "https://example.com",
                    "script": f"result['run'] = {i}; result['title'] = page.title()",
                }
            )
            assert r["statusCode"] == 200, f"Failed on invocation {i}"
            body = json.loads(r["body"])
            assert body["run"] == i
            assert body["title"] == "Example Domain"


class TestLightpandaNavigation:
    def test_page_title(self, lightpanda_container):
        r = lightpanda_container(
            {
                "url": "https://example.com",
                "script": "result['title'] = page.title()",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["title"] == "Example Domain"

    def test_page_content(self, lightpanda_container):
        r = lightpanda_container(
            {
                "url": "https://example.com",
                "script": "result['html'] = page.content()[:100]",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert "<html" in body["html"].lower()

    def test_evaluate_js(self, lightpanda_container):
        r = lightpanda_container(
            {
                "url": "https://example.com",
                "script": "result['links'] = page.evaluate('document.querySelectorAll(\"a\").length')",
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert isinstance(body["links"], (int, float))


class TestLightpandaInteraction:
    def test_todomvc_fill_and_enter(self, lightpanda_container):
        r = lightpanda_container(
            {
                "url": "https://todomvc.com/examples/react/dist/",
                "script": (
                    "page.wait_for_selector('input.new-todo')\n"
                    "page.fill('input.new-todo', 'Test item')\n"
                    "page.press('input.new-todo', 'Enter')\n"
                    "result['count'] = page.locator('ul.todo-list li').count()"
                ),
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["count"] == 1


class TestLightpandaParams:
    def test_event_params_passed_to_script(self, lightpanda_container):
        r = lightpanda_container(
            {
                "script": "result['greeting'] = f\"Hello {event['params']['name']}\"",
                "params": {"name": "Lambda"},
            }
        )
        assert r["statusCode"] == 200
        body = json.loads(r["body"])
        assert body["greeting"] == "Hello Lambda"


class TestLightpandaErrors:
    def test_script_syntax_error(self, lightpanda_container):
        r = lightpanda_container(
            {
                "script": "def broken(",
            }
        )
        assert r["statusCode"] == 500
        body = json.loads(r["body"])
        assert body["error"] == "SyntaxError"

    def test_script_runtime_error(self, lightpanda_container):
        r = lightpanda_container(
            {
                "script": "x = 1 / 0",
            }
        )
        assert r["statusCode"] == 500
        body = json.loads(r["body"])
        assert body["error"] == "ZeroDivisionError"


class TestLightpandaConsecutive:
    def test_browser_survives_multiple_invocations(self, lightpanda_container):
        for i in range(5):
            r = lightpanda_container(
                {
                    "url": "https://example.com",
                    "script": f"result['run'] = {i}; result['title'] = page.title()",
                }
            )
            assert r["statusCode"] == 200, f"Failed on invocation {i}"
            body = json.loads(r["body"])
            assert body["run"] == i
            assert body["title"] == "Example Domain"
