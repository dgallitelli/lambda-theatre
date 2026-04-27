# Fill a login form and submit it, return the resulting page info.
# Requires params: username, password
# Usage: {"url": "https://the-internet.herokuapp.com/login", "params": {"username": "tomsmith", "password": "SuperSecretPassword!"}}
# Tested against https://the-internet.herokuapp.com (Heroku demo site)

params = event.get("params", {})
if not params.get("username") or not params.get("password"):
    result["error"] = "Required params: username, password"
else:
    page.fill("#username", params["username"])
    page.fill("#password", params["password"])
    page.click("button[type='submit']")
    page.wait_for_load_state("load")

    result["url"] = page.url
    result["message"] = page.text_content("#flash") if page.locator("#flash").count() > 0 else None
    result["title"] = page.title()
