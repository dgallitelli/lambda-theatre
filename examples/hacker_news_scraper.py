"""
Scrape Hacker News front page: extract stories, visit the top N,
and collect metadata from each story's page.

Upload to S3 and invoke:
    aws s3 cp examples/hacker_news_scraper.py s3://my-bucket/scripts/
    python3 examples/invoke.py \
        --s3 s3://my-bucket/scripts/hacker_news_scraper.py \
        --param limit=5

Or invoke inline:
    python3 examples/invoke.py \
        --file examples/hacker_news_scraper.py \
        --param limit=3

Event params:
    limit   — number of stories to visit (default: 5)
"""

import time

LIMIT = int(event.get("params", {}).get("limit", 5))

# Step 1: Navigate to Hacker News
page.goto("https://news.ycombinator.com", wait_until="domcontentloaded")
page.wait_for_selector(".titleline")

# Step 2: Extract story links from the front page
stories_raw = page.evaluate("""
    () => {
        const rows = document.querySelectorAll('.athing');
        return Array.from(rows).map(row => {
            const titleEl = row.querySelector('.titleline > a');
            const subtextRow = row.nextElementSibling;
            const scoreEl = subtextRow ? subtextRow.querySelector('.score') : null;
            const ageEl = subtextRow ? subtextRow.querySelector('.age') : null;
            const commentsEl = subtextRow
                ? Array.from(subtextRow.querySelectorAll('a')).find(a => a.textContent.includes('comment'))
                : null;
            return {
                rank: row.querySelector('.rank') ? row.querySelector('.rank').textContent.trim() : null,
                title: titleEl ? titleEl.textContent.trim() : null,
                url: titleEl ? titleEl.href : null,
                points: scoreEl ? parseInt(scoreEl.textContent) : 0,
                age: ageEl ? ageEl.textContent.trim() : null,
                comments_url: commentsEl ? commentsEl.href : null,
            };
        });
    }
""")

# Step 3: Visit each story page and collect metadata
stories = []
for story in stories_raw[:LIMIT]:
    url = story.get("url")
    if not url or url.startswith("item?id="):
        story["page_title"] = None
        story["page_description"] = None
        stories.append(story)
        continue

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=10000)

        meta = page.evaluate("""
            () => {
                const title = document.title || null;
                const descEl = document.querySelector('meta[name="description"]')
                    || document.querySelector('meta[property="og:description"]');
                const desc = descEl ? descEl.getAttribute('content') : null;
                const canonical = document.querySelector('link[rel="canonical"]');
                return {
                    page_title: title,
                    page_description: desc ? desc.substring(0, 300) : null,
                    canonical_url: canonical ? canonical.href : null,
                };
            }
        """)
        story.update(meta)
    except Exception as e:
        story["page_title"] = None
        story["page_description"] = f"Error: {type(e).__name__}"

    stories.append(story)

# Step 4: Build result
result["stories"] = stories
result["count"] = len(stories)
result["scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
