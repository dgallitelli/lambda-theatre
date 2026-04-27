# Fill a login form and submit it, return the resulting page info.
# Usage: {"url": "https://the-internet.herokuapp.com/login", "params": {"username": "tomsmith", "password": "SuperSecretPassword!"}}
# Tested against https://the-internet.herokuapp.com (Heroku demo site)

page.fill("#username", event["params"]["username"])
page.fill("#password", event["params"]["password"])
page.click("button[type='submit']")
page.wait_for_load_state("load")

result["url"] = page.url
result["message"] = page.text_content("#flash") if page.locator("#flash").count() > 0 else None
result["title"] = page.title()
