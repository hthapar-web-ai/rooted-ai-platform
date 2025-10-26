from .generic_detail import scrape_index_and_details
from .utils import fetch_sitemap_urls

CANDIDATES = [
    "https://www.mbcbrokerage.ca/listings/?type=dental",
    "https://www.mbcbrokerage.ca/listings/",
]
SITEMAPS = [
    "https://www.mbcbrokerage.ca/sitemap_index.xml",
    "https://www.mbcbrokerage.ca/page-sitemap.xml",
    "https://www.mbcbrokerage.ca/post-sitemap.xml",
]
LINK_FILTERS = ["/listings", "/dental", "/practice", "/property", "/for-sale"]

def scrape():
    rows = scrape_index_and_details(
        candidates=CANDIDATES,
        link_filter_substrings=LINK_FILTERS,
        wait_selector_index="a",
        wait_selector_detail="body",
        max_links=40,
        broker_name="MBC"
    )
    if len(rows) < 2:
        urls = fetch_sitemap_urls(SITEMAPS)
        extra = scrape_index_and_details(
            candidates=urls[:40] or ["https://www.mbcbrokerage.ca/"],
            link_filter_substrings=LINK_FILTERS,
            wait_selector_index="a",
            wait_selector_detail="body",
            max_links=40,
            broker_name="MBC"
        )
        seen=set(r["url"] for r in rows)
        for r in extra:
            if r["url"] not in seen:
                rows.append(r); seen.add(r["url"])
    return rows
