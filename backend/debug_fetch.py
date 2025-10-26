import sys, time, pathlib
from scrapers.utils import fetch_html
from scrapers.browser import fetch_dynamic

URL = sys.argv[1]
out = pathlib.Path("debug_out"); out.mkdir(exist_ok=True)
ts = time.strftime("%Y%m%d-%H%M%S")

# 1) Static
try:
    html = fetch_html(URL)
    (out / f"static-{ts}.html").write_text(html, encoding="utf-8")
    print("[DEBUG] Saved", (out / f"static-{ts}.html"))
except Exception as e:
    print("[DEBUG] Static fetch failed:", e)

# 2) Dynamic
try:
    html = fetch_dynamic(URL, wait_selector="a, article, .listing, .card, .et_pb_post")
    (out / f"dynamic-{ts}.html").write_text(html, encoding="utf-8")
    print("[DEBUG] Saved", (out / f"dynamic-{ts}.html"))
except Exception as e:
    print("[DEBUG] Dynamic fetch failed:", e)
