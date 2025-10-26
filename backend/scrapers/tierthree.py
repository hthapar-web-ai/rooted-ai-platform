from .utils import absolute_link
from .browser import fetch_dynamic
from .adapters_tierthree import parse_tierthree_detail
from selectolax.parser import HTMLParser
import re

ARCHIVE = "https://tierthree.ca/listing-status/for-sale/"

RX_APPRAISED = re.compile(r'apprais(?:ed|al)\s*value', re.I)
RX_LISTING_PRICE = re.compile(r'(?:practice\s*)?listing\s*price|^price$', re.I)

def _to_num_money(s: str):
    if not s:
        return None
    t = s.strip().lower().replace(",", "")
    m = re.search(r'(\d+(?:\.\d+)?)\s*([km])\b', t)
    if m:
        val = float(m.group(1))
        return val * (1_000_000 if m.group(2).lower() == "m" else 1_000)
    m = re.search(r'(\d+(?:\.\d+)?)\s*(million|thousand)\b', t)
    if m:
        val = float(m.group(1))
        return val * (1_000_000 if m.group(2).lower() == "million" else 1_000)
    m = re.search(r'(?:C\$|\$|CAD)?\s*(\d+(?:\.\d+)?)', t, re.I)
    return float(m.group(1)) if m else None

def _extract_label_value_in_tile(tile):
    """Return (ask_from_tile, app_from_tile) by pairing label/value in same or sibling nodes."""
    ask_val = None
    app_val = None

    # scan common item containers (Elementor icon lists, short text, paragraphs)
    nodes = tile.css(".elementor-icon-list-item, .elementor-post__excerpt, .elementor-widget-text-editor, li, p, div, span, strong, b")
    for node in nodes:
        text = node.text(separator=" ", strip=True) or ""

        # same-node capture
        if RX_APPRAISED.search(text) and app_val is None:
            m = re.search(r'(?:C\$|\$|CAD)?\s*([\d,\.]+(?:\s*[kKmM]|(?:\s*(?:million|thousand)))?)', text)
            if m:
                v = _to_num_money(m.group(1))
                if v and v >= 100_000:
                    app_val = v

        if RX_LISTING_PRICE.search(text) and ask_val is None:
            m = re.search(r'(?:C\$|\$|CAD)?\s*([\d,\.]+(?:\s*[kKmM]|(?:\s*(?:million|thousand)))?)', text)
            if m:
                v = _to_num_money(m.group(1))
                if v and v >= 100_000:
                    ask_val = v

        # sibling capture (value rendered adjacent)
        if (RX_APPRAISED.search(text) and app_val is None) or (RX_LISTING_PRICE.search(text) and ask_val is None):
            # siblings within the parent container often hold the numeric value
            parent = node.parent
            if parent:
                for s in parent.css("span,div,strong,b,em,a"):
                    valtxt = s.text(strip=True)
                    if not valtxt:
                        continue
                    if RX_APPRAISED.search(valtxt) or RX_LISTING_PRICE.search(valtxt):
                        continue
                    v = _to_num_money(valtxt)
                    if v and v >= 100_000:
                        if RX_APPRAISED.search(text) and app_val is None:
                            app_val = v
                            break
                        if RX_LISTING_PRICE.search(text) and ask_val is None:
                            ask_val = v
                            break

    return ask_val, app_val

def _collect_archive_tiles(max_pages=20):
    """Return list of (url, title, ask_from_tile, app_from_tile)."""
    rows = []
    seen = set()
    for page in range(1, max_pages + 1):
        page_url = ARCHIVE if page == 1 else f"{ARCHIVE}page/{page}/"
        html = fetch_dynamic(page_url, "body")
        root = HTMLParser(html)

        tiles = root.css("article, .elementor-post, .e-loop-item, .elementor-grid-item, .post")
        if not tiles:
            tiles = root.css("div")

        found_any = False
        for tile in tiles:
            a = tile.css_first("a")
            if not a:
                continue
            href = a.attributes.get("href", "")
            u = absolute_link(page_url, href)
            if not u or "/listings/" not in u or u.rstrip("/").endswith("/listings"):
                continue
            if u in seen:
                continue

            title = a.text(strip=True) or (tile.css_first("h2,h3") and tile.css_first("h2,h3").text(strip=True)) or "View Listing"
            ask_from_tile, app_from_tile = _extract_label_value_in_tile(tile)

            rows.append((u, title, ask_from_tile, app_from_tile))
            seen.add(u)
            found_any = True

        if not found_any:
            break

    return rows

def _prov_from_url(url: str):
    m = re.search(r'/listings/([a-z]{2})\d+/?$', url, re.I)
    if not m:
        return ""
    code = m.group(1).upper()
    return code if code in ("ON","BC","AB","SK","MB","NB","NS","NL","PE","YT","NT","NU") else ""

def scrape():
    tiles = _collect_archive_tiles(max_pages=20)  # (url, title, ask_from_tile, app_from_tile)
    if not tiles:
        return []

    rows = []
    for url, title, ask_from_tile, appr_from_tile in tiles[:120]:
        province = _prov_from_url(url)

        # Enrich from detail page
        try:
            html = fetch_dynamic(url, "body")
            fields = parse_tierthree_detail(html, url=url)
        except Exception as e:
            print(f"[SCRAPER] TierThree detail fail: {url} -> {e}")
            fields = {}

        # Normalize: treat appraised value as asking price if none
        effective_price = fields.get("asking_price") or ask_from_tile or appr_from_tile

        row = {
            "broker": "TierThree",
            "title": title,
            "url": url,
            "province": fields.get("province") or province or "",
            "asking_price": effective_price,
            "collections": fields.get("collections"),
            "ebitda_or_sde": fields.get("ebitda_or_sde"),
            "equipped_ops": fields.get("equipped_ops"),
            "sqft": fields.get("sqft"),
            "appraised_value": appr_from_tile,
        }

        if any([
            row["asking_price"],
            row["collections"],
            row["ebitda_or_sde"],
            row["equipped_ops"],
            row["sqft"],
            row["appraised_value"],
        ]):
            rows.append(row)

    return rows
