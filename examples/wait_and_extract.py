# Wait for dynamic content to load, then extract structured data.
# Usage: {"url": "https://news.ycombinator.com", "params": {"selector": ".titleline > a", "limit": 10}}

selector = event["params"].get("selector", "a")
limit = event["params"].get("limit", 20)

page.wait_for_selector(selector, timeout=10000)

items = page.evaluate("""
    (args) => {
        const els = document.querySelectorAll(args.selector);
        return Array.from(els).slice(0, args.limit).map(el => ({
            text: el.textContent.trim(),
            href: el.href || null
        }));
    }
""", {"selector": selector, "limit": limit})

result["items"] = items
result["count"] = len(items)
