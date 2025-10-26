from selectolax.parser import HTMLParser
from .utils import fetch_first_ok, absolute_link, hostname
from .browser import fetch_dynamic
import re

AMOUNT_RE = re.compile(r'(?:(?:C\$|\$)\s*)?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?')
INT_RE    = re.compile(r'\b(\d{1,2})\b')  # ops rarely > 12

def _find_amount_near(txt: str, keywords, window=140, min_val=None, max_val=None):
    t = txt.lower()
    for kw in keywords:
        i = t.find(kw)
        if i != -1:
            lo = max(0, i - 20); hi = min(len(t), i + len(kw) + window)
            m = AMOUNT_RE.search(t[lo:hi])
            if m:
                raw = m.group(1).replace(',', '')
                try:
                    val = float(raw)
                    if min_val is not None and val < min_val: 
                        continue
                    if max_val is not None and val > max_val: 
                        continue
                    return val
                except:
                    pass
    return None

def _find_int_near(txt: str, keywords, window=100, min_val=None, max_val=None):
    t = txt.lower()
    for kw in keywords:
        i = t.find(kw)
        if i != -1:
            lo = max(0, i - 20); hi = min(len(t), i + len(kw) + window)
            m = INT_RE.search(t[lo:hi])
            if m:
                try:
                    val = float(m.group(1))
                    if min_val is not None and val < min_val: 
                        continue
                    if max_val is not None and val > max_val: 
                        continue
                    return val
                except:
                    pass
    return None

PROV_CODES = ['ON','BC','AB','SK','MB','NB','NS','NL','PE','YT','NT','NU']
def _guess_province(txt: str):
    t = txt.upper()
    for code in PROV_CODES:
        if f' {code} ' in f' {t} ':
            return code
    return ""

def extract_fields_from_html(html: str):
    root = HTMLParser(html)
    txt = root.text(separator=' ').strip()

    # Money fields (CAD) – guard: must be >= 10,000
    asking = _find_amount_near(txt, ['asking price','asking','list price','price'], min_val=10000)
    revenue= _find_amount_near(txt, ['collections','revenue','sales','turnover','gross'], min_val=10000)
    ebitda = _find_amount_near(txt, ['ebitda','sde','net income'], min_val=10000)

    # Ops: typically between 2 and 20
    ops    = _find_int_near(txt,   ['operatories','operatory','ops','chairs','treatment rooms'], min_val=1, max_val=20)

    # Sqft: typically 400–10,000
    sqft   = _find_amount_near(txt, ['sq ft','sqft','square feet','area','size'], min_val=400, max_val=10000)

    prov   = _guess_province(txt)

    return {
        "asking_price": asking,
        "collections": revenue,
        "ebitda_or_sde": ebitda,
        "equipped_ops": ops,
        "sqft": sqft,
        "province": prov
    }

def scrape_index_and_details(candidates, link_filter_substrings=None,
                             wait_selector_index=None, wait_selector_detail=None,
                             max_links=30, broker_name=""):
    # 1) index page (static first, dynamic fallback if few links)
    html, used = fetch_first_ok(candidates)
    root = HTMLParser(html)
    links = [a.attributes.get("href","") for a in root.css("a")] or []
    if len(links) < 5:
        html = fetch_dynamic(used, wait_selector_index or "a")
        root = HTMLParser(html)
        links = [a.attributes.get("href","") for a in root.css("a")] or []

    base_host = hostname(used)
    cleaned = []
    for href in links:
        if not href or href.startswith("#"):  # skip fragment-only links
            continue
        absu = absolute_link(used, href)
        if not absu: 
            continue
        if "#" in absu:  # skip detail anchors like /#content
            continue
        if base_host and base_host not in (hostname(absu) or ""):
            continue
        if link_filter_substrings and not any(s in absu for s in link_filter_substrings):
            continue
        cleaned.append(absu)

    # de-dupe + cap
    seen, dedup = set(), []
    for u in cleaned:
        if u in seen: continue
        seen.add(u)
        dedup.append(u)
    dedup = dedup[:max_links]

    rows = []
    for url in dedup:
        try:
            dh = fetch_dynamic(url, wait_selector_detail or "body")
            fields = extract_fields_from_html(dh)

            # Sanity: must have at least one economic field (asking/collections/ebitda)
            if not any([fields.get("asking_price"), fields.get("collections"), fields.get("ebitda_or_sde")]):
                continue

            # Drop obvious mis-assignments (e.g., collections < 100k)
            if fields.get("collections") is not None and fields["collections"] < 100000:
                fields["collections"] = None
            if fields.get("ebitda_or_sde") is not None and fields["ebitda_or_sde"] < 50000:
                fields["ebitda_or_sde"] = None

            fields["url"] = url
            rows.append(fields)
        except Exception as e:
            print(f"[SCRAPER] detail fail: {url} -> {e}")

    final = []
    for r in rows:
        final.append({
            "broker": broker_name,
            "title": "",
            "url": r.get("url",""),
            "province": r.get("province",""),
            "asking_price": r.get("asking_price"),
            "collections": r.get("collections"),
            "ebitda_or_sde": r.get("ebitda_or_sde"),
            "equipped_ops": r.get("equipped_ops"),
            "sqft": r.get("sqft"),
        })
    return final
