"""Runcrate. Public pricing feed, no key required.

Endpoint: GET https://www.runcrate.ai/api/gpu-pricing

Each GPU type carries min_price_hr, the live on-demand price for one GPU for one
hour, and available_options, how many offers are live right now. Storage and
egress are separate.

We only publish a type when two things hold. It has at least one live offer,
because the feed can keep a stale price on file for an out of stock type. And we
can name the chip without guessing: the feed does not say SXM or PCIe, so H100,
A100 and V100 (two memory sizes) are left out on purpose rather than filed under
a form the feed never stated. Anything not in WANTED is ignored.
"""

import re

from lib.common import ProviderError, fetch_json, require

KEY = "runcrate"
NAME = "Runcrate"
HOMEPAGE = "https://www.runcrate.ai"
SOURCE = "https://www.runcrate.ai/api/gpu-pricing"
KIND = "provider"
COVERAGE = ("on-demand price per GPU hour for the GPU types with a live offer whose "
            "form factor is not ambiguous. H100, A100 and V100 are left out because "
            "the feed does not say which form or memory size they are")
MIN_OFFERS = 8

# feed gpu_type -> the model string we hand to normalize(). The feed's own display
# name is used as is, except where the feed drops a word that normalize needs.
WANTED = {
    "B300": "B300",
    "B200": "B200",
    "H200": "H200",
    "H200_nvl": "H200 NVL",
    "L40S": "L40S",
    "L40": "L40",
    "RTX5090": "RTX 5090",
    "RTX4090": "RTX 4090",
    "RTX3090": "RTX 3090",
    "RTX6000Ada": "RTX 6000 Ada",
    "RTXPro6000": "RTX PRO 6000",
    "A6000": "RTX A6000",
    "A40": "A40",
    "L4": "L4",
    "A10": "A10",
}


def collect():
    data = fetch_json(SOURCE)
    gpus = data.get("gpus") if isinstance(data, dict) else None
    require(isinstance(gpus, list) and gpus, "Runcrate returned no GPU list")

    offers = []
    out_of_stock = []
    for g in gpus:
        gtype = g.get("gpu_type")
        model = WANTED.get(gtype)
        if model is None:
            continue
        if (g.get("available_options") or 0) < 1:
            out_of_stock.append(gtype)
            continue
        price = g.get("min_price_hr")
        if not isinstance(price, (int, float)) or price <= 0:
            raise ProviderError("Runcrate %s has no usable min_price_hr: %r"
                                % (gtype, price))
        m = re.match(r"(\d+)\s*GB$", str(g.get("vram") or ""))
        offers.append({
            "provider": KEY,
            "gpu_model_raw": model,
            "gpu_count": 1,
            "vram_gb": int(m.group(1)) if m else None,
            "price_total_hr": round(float(price), 4),
            "price_per_gpu_hr": round(float(price), 4),
            "pricing_type": "on-demand",
            "vcpu": None,
            "ram_gb": None,
            "region": None,
            "available": True,
            "notes": "feed type %s, %s live offers, deployment %s" % (
                gtype, g.get("available_options"),
                "/".join(g.get("deployment_types") or []) or "n/a"),
            "listing_url": HOMEPAGE,
        })

    require(
        len(offers) >= MIN_OFFERS,
        "Runcrate produced only %d rows from %d GPU types (expected >= %d)."
        % (len(offers), len(gpus), MIN_OFFERS),
    )
    return offers, {"fetched_at": data.get("fetched_at"),
                    "types_without_live_offers": out_of_stock}
