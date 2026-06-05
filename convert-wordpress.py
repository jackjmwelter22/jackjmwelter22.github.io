#!/usr/bin/env python3
"""Convert WordPress XML export to Jekyll Markdown posts."""

import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime

XML_FILE = "wordpress-export/whereintheworldiswelter.wordpress.com-2026-06-05-02_01_03/whereintheworldiswelter.wordpress.com.2026-06-05.000.xml"
OUTPUT_DIR = "_posts"

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}

def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]

def clean_content(html):
    if not html:
        return ""
    # WordPress shortcodes — strip them out
    html = re.sub(r"\[/?\w[^\]]*\]", "", html)
    return html.strip()

def parse_date(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d %H:%M:%S %z")
    except Exception:
        return "1970-01-01", "1970-01-01 00:00:00 +0000"

tree = ET.parse(XML_FILE)
root = tree.getroot()
channel = root.find("channel")

items = channel.findall("item")
posts = [
    i for i in items
    if i.find("wp:post_type", NS) is not None
    and i.find("wp:post_type", NS).text == "post"
    and i.find("wp:status", NS) is not None
    and i.find("wp:status", NS).text == "publish"
]

os.makedirs(OUTPUT_DIR, exist_ok=True)
converted = 0
skipped = 0

for post in posts:
    title_el = post.find("title")
    title = (title_el.text or "Untitled").strip()

    pub_date = post.find("pubDate")
    date_str, date_full = parse_date(pub_date.text if pub_date is not None else "")

    # Prefer WordPress slug, fall back to slugified title
    wp_slug_el = post.find("wp:post_name", NS)
    slug = (wp_slug_el.text or "").strip() or slugify(title)
    if not slug:
        slug = slugify(title)

    # Categories and tags
    categories = []
    tags = []
    for cat in post.findall("category"):
        domain = cat.get("domain", "")
        nicename = cat.get("nicename", "")
        text = cat.text or ""
        if domain == "category":
            categories.append(text)
        elif domain == "post_tag":
            tags.append(text)

    content_el = post.find("content:encoded", NS)
    content = clean_content(content_el.text if content_el is not None else "")

    excerpt_el = post.find("excerpt:encoded", NS)
    excerpt = (excerpt_el.text or "").strip()

    # Build front matter
    fm_lines = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"date: {date_full}",
    ]
    if categories:
        fm_lines.append("categories:")
        for c in categories:
            fm_lines.append(f'  - "{c}"')
    if tags:
        fm_lines.append("tags:")
        for t in tags:
            fm_lines.append(f'  - "{t}"')
    if excerpt:
        safe_excerpt = excerpt.replace('"', "'")[:200]
        fm_lines.append(f'excerpt: "{safe_excerpt}"')
    fm_lines.append("---")

    filename = f"{date_str}-{slug}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Skip if filename would collide — append post id
    if os.path.exists(filepath):
        post_id = post.find("wp:post_id", NS)
        pid = post_id.text if post_id is not None else "0"
        filename = f"{date_str}-{slug}-{pid}.md"
        filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(fm_lines))
        f.write("\n\n")
        f.write(content)
        f.write("\n")

    converted += 1

print(f"Done: {converted} posts converted, {skipped} skipped.")
print(f"Posts written to {OUTPUT_DIR}/")
