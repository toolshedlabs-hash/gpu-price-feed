"""Vast.ai. Public marketplace search API, no key required.

Endpoint: GET https://console.vast.ai/api/v0/search/asks/?q=<json>

What the numbers mean (checked against the API response's own `search` breakdown):
  dph_total = gpuCostPerHour + diskHour  (a small default disk allocation)
Bandwidth is billed separately by the host and is NOT in this number.

We only list machines Vast marks `verified`. The cheapest listings on Vast are
often unverified or deverified hosts. Quoting those as "the cheapest H100" would
be technically true and practically misleading, so we filter and say so.

COVERAGE, read this before asking why a GPU is missing. Vast's search API answers
a query about one gpu_name at a time and caps a broad query at 64 rows, so there
is no "give me everything" call. We therefore do two things per run:
  1. query a fixed base list of gpu_name values (TRACKED below), and
  2. sample the marketplace from several angles (cheapest, dearest, most GPUs,
     most and least VRAM, most reliable) and query anything new that turns up.
Every name we ended up querying is written to `meta.models_queried`, the ones the
sample added are in `meta.models_discovered`, and the ones with no verified stock
this run are in `meta.models_with_no_stock`. A model that is neither in the base
list nor in the sample window will still be missing, and that is the honest limit
of this collector.
"""

import json
import urllib.parse

from lib.common import ProviderError, fetch_json, require
from lib.normalize import round_vram

KEY = "vastai"
NAME = "Vast.ai"
HOMEPAGE = "https://vast.ai"
SOURCE = "https://console.vast.ai/api/v0/search/asks/"
KIND = "marketplace"
MIN_OFFERS = 12
COVERAGE = ("a fixed base list of GPU names plus whatever a six angle sample of "
            "the marketplace turns up; verified hosts only; single GPU offers "
            "preferred. A model outside both the base list and the sample does "
            "not appear")

# Vast's own gpu_name vocabulary. Discovered from the live API, kept explicit so a
# rename upstream shows up as a missing model rather than as silence. Discovery
# below adds to this list, it does not replace it.
TRACKED = [
    "B300", "B200", "H200 NVL", "H200", "H100 NVL", "H100 SXM", "H100 PCIE",
    "A100 SXM4", "A100 PCIE", "L40S", "L40", "L4", "A40", "A10",
    "RTX PRO 6000 WS", "RTX PRO 6000 S", "RTX 6000Ada", "RTX A6000", "RTX A5000",
    "RTX A4000", "RTX 5090", "RTX 4090", "RTX 4080", "RTX 3090", "RTX 3080",
    "Tesla V100", "Tesla T4",
]

# A broad query comes back capped, so we ask from several directions and union
# the names. Cheapest and dearest catch the ends of the price range, most GPUs
# catches the big rigs, VRAM catches the very new and the very old cards.
DISCOVERY_ORDERS = [
    ["dph_total", "asc"], ["dph_total", "desc"], ["num_gpus", "desc"],
    ["gpu_ram", "desc"], ["gpu_ram", "asc"], ["reliability2", "desc"],
]

# How many cheapest offers to keep per model. Enough to show the market has depth,
# small enough that the JSON stays readable.
KEEP_PER_MODEL = 3


def _query(q):
    url = SOURCE + "?q=" + urllib.parse.quote(json.dumps(q))
    d = fetch_json(url)
    if not isinstance(d, dict) or "offers" not in d:
        raise ProviderError("unexpected Vast response shape: %s" % str(d)[:200])
    return d["offers"]


def _row(o):
    for f in ("dph_total", "num_gpus", "gpu_name"):
        if o.get(f) is None:
            raise ProviderError("Vast offer missing field %s" % f)
    n = int(o["num_gpus"])
    require(n >= 1, "Vast offer with num_gpus=%s" % n)
    total = float(o["dph_total"])
    return {
        "provider": KEY,
        "gpu_model_raw": o["gpu_name"],
        "gpu_count": n,
        "vram_mb": o.get("gpu_ram"),
        "vram_gb": round_vram(o.get("gpu_ram")),
        "price_total_hr": round(total, 4),
        "price_per_gpu_hr": round(total / n, 4),
        "pricing_type": "on-demand",
        "vcpu": o.get("cpu_cores_effective"),
        "ram_gb": round(o["cpu_ram"] / 1024.0) if o.get("cpu_ram") else None,
        "disk_gb": round(o["disk_space"]) if o.get("disk_space") else None,
        "region": (o.get("geolocation") or "").strip().strip(",").strip() or None,
        "available": bool(o.get("rentable")),
        "notes": "verified host, reliability %.3f" % (o.get("reliability2") or 0),
        "listing_url": "https://cloud.vast.ai/create/",
    }


def _discover():
    """Names visible in a sample of the live marketplace, in a stable order."""
    seen = []
    for order in DISCOVERY_ORDERS:
        rows = _query({
            "rentable": {"eq": True},
            "verified": {"eq": True},
            "order": [order],
            "type": "on-demand",
            "limit": 1000,
        })
        for o in rows:
            name = (o.get("gpu_name") or "").strip()
            if name and name not in seen:
                seen.append(name)
    require(seen, "Vast discovery sample returned no gpu_name values at all")
    return seen


def collect():
    offers = []
    missing = []
    discovered = [n for n in _discover() if n not in TRACKED]
    queried = TRACKED + discovered
    for model in queried:
        base = {
            "gpu_name": {"eq": model},
            "rentable": {"eq": True},
            "verified": {"eq": True},
            "order": [["dph_total", "asc"]],
            "type": "on-demand",
            "limit": 64,
        }
        q = dict(base, num_gpus={"eq": 1})
        got = _query(q)
        if not got:
            q = dict(base, num_gpus={"gte": 1})
            got = _query(q)
        if not got:
            missing.append(model)
            continue
        got.sort(key=lambda o: float(o["dph_total"]) / max(1, int(o["num_gpus"])))
        for o in got[:KEEP_PER_MODEL]:
            offers.append(_row(o))

    require(
        len(offers) >= MIN_OFFERS,
        "Vast returned only %d offers across %d queried models (expected >= %d). "
        "The API shape or the gpu_name vocabulary probably changed."
        % (len(offers), len(queried), MIN_OFFERS),
    )
    return offers, {
        "models_queried": queried,
        "models_discovered": discovered,
        "models_with_no_stock": missing,
    }
