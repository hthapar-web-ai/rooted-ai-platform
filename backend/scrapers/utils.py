import re, time, httpx
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser

DEFAULT_HEADERS = {
    "User-Agent": "RootedBot/1.0 (+https://rooted.ai) contact: dev@rooted.ai"
}

def fetch_html(url: str, timeout=30) -> str:
    with httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text

def fetch_first_ok(candidates, timeout=30):
    last_err = None
    for u in candidates:
        try:
            html = fetch_html(u, timeout=timeout)
            print(f"[SCRAPER] OK: {u}")
            return html, u
        except Exception as e:
            last_err = e
            print(f"[SCRAPER] FAIL: {u} -> {e}")
            continue
    if last_err:
        raise last_err
    raise RuntimeError("No candidates provided")

def parse_number(s: str):
    if not s: return None
    s = s.replace(",","").replace("$","").replace("CAD","").replace("C$","").strip()
    m = re.search(r"-?[\d]+(\.\d+)?", s)
    return float(m.group(0)) if m else None

def sleep_polite(seconds=1.0): time.sleep(seconds)

def text(el):
    if el is None: return ""
    if isinstance(el, str): return el.strip()
    if hasattr(el, "text"): return el.text(strip=True)
    return str(el).strip()

def absolute_link(base, href: str):
    if not href: return None
    return urljoin(base, href)

def hostname(u: str):
    try:
        return urlparse(u).hostname or ""
    except:
        return ""

def fetch_sitemap_urls(base_sitemap_urls):
    """Return list of URLs from one or more sitemap.xml endpoints."""
    out = []
    with httpx.Client(headers=DEFAULT_HEADERS, timeout=30, follow_redirects=True) as c:
        for sm in base_sitemap_urls:
            try:
                r = c.get(sm)
                r.raise_for_status()
                # naive extraction of <loc>...</loc>
                locs = re.findall(r"<loc>(.*?)</loc>", r.text, flags=re.IGNORECASE)
                out.extend(locs)
                print(f"[SCRAPER] sitemap OK: {sm} -> {len(locs)} urls")
            except Exception as e:
                print(f"[SCRAPER] sitemap FAIL: {sm} -> {e}")
                continue
    return out
