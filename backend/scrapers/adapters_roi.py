from selectolax.parser import HTMLParser
import re

def _to_num(s: str):
    if not s: return None
    s = (s.replace("\u00a0"," ")
           .replace(",", "")
           .replace("CAD","")
           .replace("C$","")
           .replace("$","")
           .strip())
    m = re.search(r'(-?\d+(?:\.\d+)?)', s)
    try:
        return float(m.group(1)) if m else None
    except:
        return None

PROV_CODES = ['ON','BC','AB','SK','MB','NB','NS','NL','PE','YT','NT','NU']

def _guess_province(txt: str):
    up = " " + txt.upper() + " "
    for code in PROV_CODES:
        if f" {code} " in up:
            return code
    return ""

LABEL_ALIASES = {
    "asking_price":  ["asking price", "list price", "price"],
    "collections":   ["gross revenue", "revenue", "collections", "annual production", "turnover", "gross"],
    "ebitda_or_sde": ["cash earnings", "ebitda", "sde", "net income", "cash flow"],
    "equipped_ops":  ["operatories", "operatory", "ops", "chairs", "treatment rooms"],
    "sqft":          ["square feet", "sq ft", "sqft", "area", "size"],
}

def _match_label(text: str, target_list):
    t = text.strip().lower()
    for key in target_list:
        if key in t:
            return True
    return False

def _neighbors_text(node):
    """Text of node plus immediate next sibling(s) to catch 'Label' + 'Value' patterns."""
    bits = [node.text(strip=True)]
    sib = node.next
    if sib:
        bits.append(sib.text(strip=True))
    # sometimes value is in the parent then a span/div
    if node.parent:
        children = node.parent.css("span,div,dd,td")
        for ch in children[:3]:
            bits.append(ch.text(strip=True))
    return " | ".join([b for b in bits if b])

def _extract_by_dom(root: HTMLParser):
    out = {k: None for k in LABEL_ALIASES.keys()}

    # 1) try definition lists (dl/dt/dd)
    for dl in root.css("dl"):
        dts = dl.css("dt")
        dds = dl.css("dd")
        for i, dt in enumerate(dts):
            label = dt.text(strip=True)
            if not label: continue
            valtxt = ""
            if i < len(dds):
                valtxt = dds[i].text(strip=True)
            for field, aliases in LABEL_ALIASES.items():
                if _match_label(label, aliases):
                    if field in ("equipped_ops",):
                        num = _to_num(valtxt or label)
                    else:
                        num = _to_num(valtxt or label)
                    if field == "sqft" and num and (num < 350 or num > 12000): num = None
                    if field == "equipped_ops" and num and (num < 1 or num > 25): num = None
                    if out[field] is None and num is not None:
                        out[field] = num

    # 2) try tables
    for row in root.css("table tr"):
        cells = row.css("th,td")
        if len(cells) >= 2:
            label = cells[0].text(strip=True)
            value = cells[1].text(strip=True)
            for field, aliases in LABEL_ALIASES.items():
                if _match_label(label, aliases):
                    num = _to_num(value or label)
                    if field == "sqft" and num and (num < 350 or num > 12000): num = None
                    if field == "equipped_ops" and num and (num < 1 or num > 25): num = None
                    if out[field] is None and num is not None:
                        out[field] = num

    # 3) generic label elements: strong/b tags or labels preceding values
    for lab in root.css("strong, b, th, .label, .listing__label, .et_pb_text_inner strong"):
        label = lab.text(strip=True)
        if not label: continue
        bundle = _neighbors_text(lab)
        for field, aliases in LABEL_ALIASES.items():
            if _match_label(label, aliases):
                num = _to_num(bundle)
                if field == "sqft" and num and (num < 350 or num > 12000): num = None
                if field == "equipped_ops" and num and (num < 1 or num > 25): num = None
                if out[field] is None and num is not None:
                    out[field] = num

    # 4) fallback: full-text proximity search (last resort)
    full = root.text(separator=' ').strip()
    def near(keywords, minv=None):
        t = full.lower()
        for kw in keywords:
            i = t.find(kw)
            if i != -1:
                lo = max(0, i-24); hi = min(len(t), i+len(kw)+140)
                sub = full[lo:hi]
                n = _to_num(sub)
                if n and (minv is None or n >= minv):
                    return n
        return None

    if out["asking_price"] is None:
        out["asking_price"] = near(LABEL_ALIASES["asking_price"], 10000)
    if out["collections"] is None:
        out["collections"] = near(LABEL_ALIASES["collections"], 100000)
    if out["ebitda_or_sde"] is None:
        out["ebitda_or_sde"] = near(LABEL_ALIASES["ebitda_or_sde"], 50000)
    if out["equipped_ops"] is None:
        # quick int near labels
        m = re.search(r'(?:ops|operatories|operatory|chairs|treatment rooms)\D{0,12}(\d{1,2})', full, re.I)
        if m:
            num = _to_num(m.group(1))
            if num and 1 <= num <= 25:
                out["equipped_ops"] = num
    if out["sqft"] is None:
        m = re.search(r'(\d[\d,\.]{3,})\s*(?:sq\.?\s*ft|sqft|square\s*feet)', full, re.I)
        if m:
            num = _to_num(m.group(1))
            if num and 350 <= num <= 12000:
                out["sqft"] = num

    return out

def parse_roi_detail(html: str):
    root = HTMLParser(html)
    fields = _extract_by_dom(root)
    prov = _guess_province(root.text(separator=' '))
    fields["province"] = prov
    # also try to catch explicit "Appraised Value" if present, for later QC
    m = re.search(r'Appraised Value\s*[:\-]?\s*\$?\s*([\d,\.]+)', root.text(separator=' '), re.I)
    fields["appraised_value"] = _to_num(m.group(1)) if m else None
    return fields
