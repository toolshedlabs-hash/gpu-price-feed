"""Vultr Cloud GPU. Public plan catalog, no key required.

Endpoint: GET https://api.vultr.com/v2/plans?type=vcg

Vultr sells fractional GPUs. A plan can be "1/8" of an A16. A per GPU hourly rate
computed from a fraction would be a number nobody can actually buy, so we record
gpu_fraction and only set price_per_gpu_hr on plans that give you at least one
whole GPU. Fractional plans stay in the data with price_per_gpu_hr = null.

Vultr bare metal GPU plans use a different endpoint and are not covered here.
"""

from lib.common import ProviderError, fetch_json, require

KEY = "vultr"
NAME = "Vultr"
HOMEPAGE = "https://www.vultr.com"
SOURCE = "https://api.vultr.com/v2/plans?type=vcg&per_page=500"
KIND = "provider"
COVERAGE = ("cloud GPU (vcg) plans only, fractional and whole. Vultr bare metal GPU "
            "plans live on another endpoint and are not covered")
MIN_OFFERS = 8


def _fraction(raw):
    """'1/8' -> 0.125, '1' -> 1.0, 8 -> 8.0."""
    if raw is None:
        return None
    s = str(raw).strip()
    try:
        if "/" in s:
            a, b = s.split("/", 1)
            return float(a) / float(b)
        return float(s)
    except (ValueError, ZeroDivisionError):
        raise ProviderError("Vultr gpu_count %r is not parseable" % (raw,))


def collect():
    data = fetch_json(SOURCE)
    plans = data.get("plans")
    require(isinstance(plans, list) and plans, "Vultr returned no vcg plans")
    meta = data.get("meta") or {}
    nxt = (meta.get("links") or {}).get("next")
    require(
        not nxt,
        "Vultr response is paginated and we only read page one. Increase per_page.",
    )

    offers = []
    fractional = 0
    for p in plans:
        brand = p.get("gpu_brand")
        if not brand or brand == "none":
            continue
        raw = p.get("gpu_type")
        require(raw, "Vultr plan %s has a gpu_brand but no gpu_type" % p.get("id"))
        frac = _fraction(p.get("gpu_count"))
        price = p.get("hourly_cost")
        if price is None:
            raise ProviderError("Vultr plan %s has no hourly_cost" % p.get("id"))
        price = float(price)
        if price <= 0:
            continue
        whole = frac is not None and frac >= 1
        if not whole:
            fractional += 1
        # gpu_vram_gb is the VRAM allocated to the whole plan, so on a 2 GPU plan
        # it is the sum. Only divide it out when the plan owns whole GPUs.
        alloc = p.get("gpu_vram_gb")
        vram_per_gpu = int(round(alloc / frac)) if (whole and alloc) else None
        offers.append({
            "provider": KEY,
            "gpu_model_raw": raw,
            "gpu_count": round(frac, 4),
            "gpu_fraction": round(frac, 4),
            "vram_gb": vram_per_gpu,
            "vram_gb_allocated": alloc,
            "price_total_hr": round(price, 4),
            "price_per_gpu_hr": round(price / frac, 4) if whole else None,
            "pricing_type": "on-demand",
            "vcpu": p.get("vcpu_count"),
            "ram_gb": int(round(p["ram"] / 1024.0)) if p.get("ram") else None,
            "region": ",".join(p.get("locations") or []) or None,
            "available": None,
            "notes": "plan %s; GPU share %s; %s GB of VRAM allocated"
                     % (p.get("id"), p.get("gpu_count"), p.get("gpu_vram_gb")),
            "listing_url": "https://www.vultr.com/products/cloud-gpu/",
        })

    require(
        len(offers) >= MIN_OFFERS,
        "Vultr produced only %d GPU plans (expected >= %d)."
        % (len(offers), MIN_OFFERS),
    )
    return offers, {"fractional_plans": fractional, "total_vcg_plans": len(plans)}
