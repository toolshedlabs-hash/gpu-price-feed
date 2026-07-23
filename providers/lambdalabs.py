"""Lambda. Parsed from the public pricing page.

Source: https://lambda.ai/service/gpu-cloud

Lambda's instance API needs a key, so we read the published pricing table. The
table is machine readable: each row carries data-plan and data-label attributes,
and the price column is already expressed per GPU per hour. There are four tabs
(8x, 4x, 2x, 1x); we read all of them and record the GPU count with each row.

Sales tax is excluded from these numbers, which is what the page footnote says.
"""

import re

from lib.common import ProviderError, fetch_text, require, unescape_unicode

KEY = "lambdalabs"
NAME = "Lambda"
HOMEPAGE = "https://lambda.ai"
SOURCE = "https://lambda.ai/service/gpu-cloud"
KIND = "provider"
COVERAGE = ("every row of the public pricing page, all four GPU count tabs. Lambda's "
            "instance API needs a key so on-demand availability is not covered")
MIN_OFFERS = 15

TAB_RE = re.compile(r'class="_tabButton[^"]*"[^>]*>(\d+)x</button>')
TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
ROW_RE = re.compile(r'<tr[^>]*data-plan="([^"]+)"[^>]*>(.*?)</tr>', re.S)
CELL_RE = re.compile(r'data-label="([^"]*)"[^>]*>(.*?)</t[dh]>', re.S)


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def _first_num(s):
    m = re.search(r"([\d.]+)", s.replace(",", ""))
    return float(m.group(1)) if m else None


def collect():
    html = unescape_unicode(fetch_text(SOURCE))

    tabs = TAB_RE.findall(html)
    require(
        tabs, "Lambda page: could not find the GPU count tabs. Page layout changed."
    )

    # The page also ships a JSON-escaped copy of the same tables inside a JS blob
    # for client side hydration. Requiring a literal data-plan attribute keeps us
    # on the real rendered tables and off the duplicate.
    tables = [
        t for t in TABLE_RE.findall(html)
        if "PRICE/GPU/HR" in t and 'data-plan="' in t
    ]
    require(
        tables,
        "Lambda page: no pricing table with a PRICE/GPU/HR column. Layout changed.",
    )
    require(
        len(tables) == len(tabs),
        "Lambda page: %d tabs but %d pricing tables. Cannot map counts to rows "
        "safely, refusing to guess." % (len(tabs), len(tables)),
    )

    offers = []
    for count_str, table in zip(tabs, tables):
        n = int(count_str)
        for plan, body in ROW_RE.findall(table):
            cells = {k.strip(): _text(v) for k, v in CELL_RE.findall(body)}
            price_key = next(
                (k for k in cells if k.upper().startswith("PRICE/GPU/HR")), None
            )
            if price_key is None:
                raise ProviderError(
                    "Lambda row %r has no PRICE/GPU/HR cell: %s" % (plan, cells)
                )
            per_gpu = _first_num(cells[price_key])
            if per_gpu is None:
                raise ProviderError(
                    "Lambda row %r has an unparseable price %r"
                    % (plan, cells[price_key])
                )
            vram = _first_num(cells.get("VRAM/GPU", "")) or None
            vcpu = _first_num(cells.get("vCPUs", "")) or None
            ram = _first_num(cells.get("RAM", "")) or None
            offers.append({
                "provider": KEY,
                "gpu_model_raw": plan,
                "gpu_count": n,
                "vram_gb": int(vram) if vram else None,
                "price_total_hr": round(per_gpu * n, 4),
                "price_per_gpu_hr": round(per_gpu, 4),
                "pricing_type": "on-demand",
                "vcpu": int(vcpu) if vcpu else None,
                "ram_gb": int(ram) if ram else None,
                "region": None,
                "available": None,
                "notes": "%dx config, storage %s, excludes sales tax"
                         % (n, cells.get("STORAGE") or "n/a"),
                "listing_url": SOURCE,
            })

    require(
        len(offers) >= MIN_OFFERS,
        "Lambda produced only %d rows (expected >= %d). Page layout changed."
        % (len(offers), MIN_OFFERS),
    )
    return offers, {"tabs": tabs}
