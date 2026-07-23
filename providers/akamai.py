"""Akamai Cloud (Linode). Public plan catalog, no key required.

Endpoint: GET https://api.linode.com/v4/linode/types

The GPU model only appears in the plan label ("Dedicated 32GB + RTX6000 GPU x1",
"RTX4000 Ada x2 Small"), so we read the model out of the label and keep the raw
label on every row. Plans with `gpus` = 0 are skipped, which also drops the
NETINT video transcoding accelerators. Those are not GPUs and do not belong in a
GPU price table.
"""

import re

from lib.common import ProviderError, fetch_json, require

KEY = "akamai"
NAME = "Akamai Cloud (Linode)"
HOMEPAGE = "https://www.linode.com"
SOURCE = "https://api.linode.com/v4/linode/types"
KIND = "provider"
MIN_OFFERS = 5

LABEL_RE = re.compile(
    r"(?:\+\s*)?(RTX\s?\d{4}(?:\s?Ada)?|A100|H100|L40S?|L4)\s*(?:GPU\s*)?x?(\d+)?",
    re.I,
)


def _model_from_label(label):
    m = LABEL_RE.search(label)
    if not m:
        raise ProviderError(
            "Akamai plan label %r does not contain a recognisable GPU model. "
            "The naming convention changed." % label
        )
    return m.group(1).strip()


def collect():
    data = fetch_json(SOURCE)
    types = data.get("data")
    require(isinstance(types, list) and types, "Akamai returned no linode types")
    require(
        data.get("page") == data.get("pages") or data.get("pages") == 1,
        "Akamai returned a paginated response we are not handling: page %s of %s"
        % (data.get("page"), data.get("pages")),
    )

    offers = []
    for t in types:
        n = t.get("gpus") or 0
        if not n:
            continue
        label = t.get("label") or ""
        model = _model_from_label(label)
        price = ((t.get("price") or {}).get("hourly"))
        if price is None:
            raise ProviderError("Akamai plan %s has no hourly price" % t.get("id"))
        price = float(price)
        if price <= 0:
            continue
        offers.append({
            "provider": KEY,
            "gpu_model_raw": model,
            "gpu_count": int(n),
            "vram_gb": None,
            "price_total_hr": round(price, 4),
            "price_per_gpu_hr": round(price / n, 4),
            "pricing_type": "on-demand",
            "vcpu": t.get("vcpus"),
            "ram_gb": int(round(t["memory"] / 1024.0)) if t.get("memory") else None,
            "region": None,
            "available": None,
            "notes": "plan %s (%s)" % (t.get("id"), label),
            "listing_url": "https://www.linode.com/products/gpu/",
        })

    require(
        len(offers) >= MIN_OFFERS,
        "Akamai produced only %d GPU plans (expected >= %d)."
        % (len(offers), MIN_OFFERS),
    )
    return offers, {"total_plans": len(types)}
