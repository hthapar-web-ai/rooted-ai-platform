from .utils import fetch_first_ok, fetch_sitemap_urls, absolute_link, hostname
from .browser import fetch_dynamic
from selectolax.parser import HTMLParser
from .adapters_roi import parse_roi_detail

INDEX_CANDIDATES = [
    "https://www.roicorp.com/practices-for-sale/dental/",
    "https://www.roicorp.com/practices-for-sale/",
]
SITEMAPS = [
    "https://roicorp.com/sitemap_index.xml",
    "https://www.roicorp.com/sitemap_index.xml",
    "https://roicorp.com/post-sitemap.xml",
    "https://www.roicorp.com/post-sitemap.xml",
]

def _clean_row(r):
    # sanity ranges
    if r.get("collections") is not None and r["collections"] < 100000:
        r["collections"] = None
    if r.get("ebitda_or_sde") is not None and r["ebitda_or_sde"] < 50000:
        r["ebitda_or_sde"] = None
    if r.get("sqft") is not None and (r["sqft"] < 350 or r["sqft"] > 12000):
        r["sqft"] = None
    if r.get("equipped_ops") is not None and (r["equipped_ops"] < 1 or r["equipped_ops"] > 25):
        r["equipped_ops"] = None
    return r

def _detail_urls_from_index():
    html, used = fetch_first_ok(INDEX_CANDIDATES)
    root = HTMLParser(html)
    links = [a.attributes.get("href","") for a in root.css("a")] or []
    if len(links) < 5:
        html = fetch_dynamic(used, "a")
        root = HTMLParser(html)
        links = [a.attributes.get("href","") for a in root.css("a")] or []
    out = []
    for href in links:
        u = absolute_link(used, href)
        if not u: continue
        if "/listings/" in u and not u.endswith(("/listings/","/listings")) and "#" not in u:
            out.append(u)
    # de-dupe
    return list(dict.fromkeys(out))

def scrape():
    # 1) try sitemap (best source of real listing URLs)
    urls = fetch_sitemap_urls(SITEMAPS)
    detail_urls = [u for u in urls if "/listings/" in u and "#" not in u and not u.rstrip("/").endswith("/listings")]
    # 2) add index-derived links (some listings may not be in sitemap)
    detail_urls += _detail_urls_from_index()
    # de-dupe
    detail_urls = list(dict.fromkeys(detail_urls))

    rows = []
    for url in detail_urls[:80]:  # cap for politeness
        try:
            html = fetch_dynamic(url, "body")
            fields = parse_roi_detail(html)
            # must have at least one econ signal:
            if not any([fields.get("asking_price"), fields.get("collections"), fields.get("ebitda_or_sde")]):
                continue
            fields = _clean_row(fields)
            rows.append({
                "broker": "ROI",
                "title": "",
                "url": url,
                "province": fields.get("province",""),
                "asking_price": fields.get("asking_price"),
                "collections": fields.get("collections"),
                "ebitda_or_sde": fields.get("ebitda_or_sde"),
                "equipped_ops": fields.get("equipped_ops"),
                "sqft": fields.get("sqft"),
            })
        except Exception as e:
            print(f"[SCRAPER] ROI detail fail: {url} -> {e}")
            continue
    return rows
