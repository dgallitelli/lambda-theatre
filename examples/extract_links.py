# Extract all links from a page.
# Usage: {"url": "https://example.com", "script": <this file>}

links = page.evaluate("""
    Array.from(document.querySelectorAll('a[href]')).map(a => ({
        text: a.textContent.trim(),
        href: a.href
    }))
""")
result["links"] = links
result["count"] = len(links)
