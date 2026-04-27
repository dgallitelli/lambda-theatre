# Add items to a TodoMVC React app and return the count.
# Usage: {"url": "https://todomvc.com/examples/react/dist/", "params": {"todos": ["A", "B"]}}

page.wait_for_selector("input.new-todo")

for item in event["params"]["todos"]:
    page.fill("input.new-todo", item)
    page.press("input.new-todo", "Enter")

result["count"] = page.locator("ul.todo-list li").count()
result["items"] = page.evaluate(
    "Array.from(document.querySelectorAll('ul.todo-list li label'))"
    ".map(l => l.textContent)"
)
