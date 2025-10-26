from selectolax.parser import HTMLParser
import re
from urllib.parse import urlparse

def _num_plain(s: str):
    if not s: return None
    s = (s.replace("\u00a0"," ").replace(",", "").replace("CAD","").replace("C$","").replace("$","").strip())
    m = re.search(r'(-?\d+(?:\.\d+)?)', s)
    try:
        return float(m.group(1)) if m else None
    except:
        return None

def _num_money(s: str):
    """Parse money with optional K/M suffix, with or without currency symbol."""
    if not s: return None
    t = s.replace("\u00a0"," ").strip()
    # Detect suffix first
    m = re.search(r'(-?\d+(?:\.\d+)?)\s*([kKmM])\b', t)
    if m:
        val = float(m.group(1))
        suf = m.group(2).lower()
        return val * (1_000_000 if suf == 'm' else 1_000)
    # Otherwise plain numeric (may still have $ or commas)
    return _num_plain(t)

def _money_present(s: str) -> bool:
    if not s: return False
    return bool(re.search(r'(?:C\$|\$|CAD|\b[0-9]+(?:\.[0-9]+)?\s*[kKmM]\b)', s, re.I))

PROV = ['ON','BC','AB','SK','MB','NB','NS','NL','PE','YT','NT','NU']

def _prov_from_text(txt: str):
    up = " "+txt.upper()+" "
    for p in PROV:
        if f" {p} " in up: return p
    return ""

def _prov_from_url(url: str):
    try:
        slug = urlparse(url).path.rstrip('/').split('/')[-1]
        m = re.match(r'([a-z]{2})\d+', slug, re.I)
        if m:
            p = m.group(1).upper()
            if p in PROV: return p
    except:
        pass
    return ""

LABELS = {
    "asking_price":  ["asking price","list price","offering price","purchase price","price"],
    "collections":   ["gross revenue","practice gross revenue","revenue","collections","annual production","turnover","gross billings","billings"],
    "ebitda_or_sde": ["normalized ebitda","ebitda","sde","cash earnings","adjusted cash earnings","cash flow","net income","seller's discretionary earnings"],
    "equipped_ops":  ["operatories","operatory","ops","chairs","treatment rooms"],
    "sqft":          ["premises size","square feet","sq ft","sqft","area","size"],
}

def _match(label: str, options):
    t = (label or "").strip().lower()
    return any(k in t for k in options)

def _neighbors_bundle(node):
    bits = [node.text(strip=True)]
    if node.next: bits.append(node.next.text(strip=True))
    if node.parent:
        for ch in node.parent.css("span,div,dd,td"):
            txt = ch.text(strip=True)
            if txt: bits.append(txt)
    return " ".join(bits)

def parse_tierthree_detail(html: str, url: str = ""):
    root = HTMLParser(html)
    out = {k: None for k in LABELS}

    # 1) Elementor “listing facts” often appear in definition lists or info blocks
    # DL blocks
    for dl in root.css("dl"):
        dts, dds = dl.css("dt"), dl.css("dd")
        for i, dt in enumerate(dts):
            label = dt.text(strip=True)
            val = dds[i].text(strip=True) if i < len(dds) else ""
            for fld, aliases in LABELS.items():
                if _match(label, aliases):
                    if fld in ("asking_price","collections","ebitda_or_sde"):
                        if not (_money_present(label) or _money_present(val)):
                            continue
                        num = _num_money(val or label)
                    elif fld == "equipped_ops":
                        num = _num_plain(val or label)
                    else:
                        num = _num_plain(val or label)
                    if fld == "sqft" and num and not (350 <= num <= 12000): num = None
                    if fld == "equipped_ops" and num and not (1 <= num <= 25): num = None
                    if out[fld] is None and num is not None:
                        out[fld] = num

    # 2) Tables
    for tr in root.css("table tr"):
        tds = tr.css("th,td")
        if len(tds) >= 2:
            label = tds[0].text(strip=True)
            val = tds[1].text(strip=True)
            for fld, aliases in LABELS.items():
                if _match(label, aliases):
                    if fld in ("asking_price","collections","ebitda_or_sde"):
                        if not (_money_present(label) or _money_present(val)):
                            continue
                        num = _num_money(val or label)
                    elif fld == "equipped_ops":
                        num = _num_plain(val or label)
                    else:
                        num = _num_plain(val or label)
                    if fld == "sqft" and num and not (350 <= num <= 12000): num = None
                    if fld == "equipped_ops" and num and not (1 <= num <= 25): num = None
                    if out[fld] is None and num is not None:
                        out[fld] = num

    # 3) Elementor “icon-list” pattern (common on TT)
    for li in root.css(".elementor-icon-list-item, .elementor-widget-text-editor li, li"):
        text = li.text(separator=' ', strip=True) or ""
        for fld, aliases in LABELS.items():
            if _match(text, aliases):
                if fld in ("asking_price","collections","ebitda_or_sde"):
                    if not _money_present(text): 
                        continue
                    num = _num_money(text)
                elif fld == "equipped_ops":
                    m = re.search(r'(\d{1,2})\s*(?:ops|operatories|operatory|chairs|treatment rooms)', text, re.I)
                    num = _num_plain(m.group(1)) if m else None
                else:
                    num = _num_plain(text)
                if fld == "sqft" and num and not (350 <= num <= 12000): num = None
                if fld == "equipped_ops" and num and not (1 <= num <= 25): num = None
                if out[fld] is None and num is not None:
                    out[fld] = num

    # 4) Fallback proximity (still require $/CAD or K/M for money)
    full = root.text(separator=" ").strip()
    if out["equipped_ops"] is None:
        m = re.search(r'(?:ops|operatories|operatory|chairs|treatment rooms)\D{0,12}(\d{1,2})', full, re.I)
        if m:
            n = _num_plain(m.group(1))
            if n and 1 <= n <= 25: out["equipped_ops"] = n
    if out["sqft"] is None:
        m = re.search(r'(\d[\d,\.]{3,})\s*(?:sq\.?\s*ft|sqft|square\s*feet)', full, re.I)
        if m:
            n = _num_plain(m.group(1))
            if n and 350 <= n <= 12000: out["sqft"] = n

    # Province — URL takes precedence
    p_url = _prov_from_url(url or "")
    p_txt = _prov_from_text(full)
    out["province"] = p_url or p_txt or ""
    # Minimums for money
    if out["collections"] is not None and out["collections"] < 100000: out["collections"] = None
    if out["ebitda_or_sde"] is not None and out["ebitda_or_sde"] < 50000: out["ebitda_or_sde"] = None

    return out
