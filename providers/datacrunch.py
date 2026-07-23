"""DataCrunch. Public instance-type catalog, no key required.

Endpoint: GET https://api.datacrunch.io/v1/instance-types

Each entry carries price_per_hour (fixed on-demand) and spot_price for the whole
instance, so we divide by the GPU count to get a per GPU rate. Storage is billed
separately. Entries with zero GPUs are skipped.
"""

from lib.common import ProviderError, fetch_json, require

KEY = "datacrunch"
NAME = "DataCrunch"
HOMEPAGE = "https://datacrunch.io"
SOURCE = "https://api.datacrunch.io/v1/instance-types"
KIND = "provider"
COVERAGE = "every instance type in the public catalog that has a GPU, on-demand and spot"
MIN_OFFERS = 20


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ProviderError("DataCrunch non-numeric price %r" % (v,))
    return f


def collect():
    data = fetch_json(SOURCE)
    require(isinstance(data, list) and data, "DataCrunch returned no instance types")

    offers = []
    skipped = []
    for it in data:
        gpu = it.get("gpu") or {}
        n = gpu.get("number_of_gpus") or 0
        if not n:
            skipped.append(it.get("instance_type"))
            continue
        model = it.get("name") or it.get("model")
        require(model, "DataCrunch instance %s has no model name" % it.get("id"))
        # gpu_memory is the total across all GPUs in the instance.
        total_vram = (it.get("gpu_memory") or {}).get("size_in_gigabytes")
        vram = int(round(total_vram / n)) if total_vram else None
        base = {
            "provider": KEY,
            "gpu_model_raw": model,
            "gpu_count": int(n),
            "vram_gb": vram,
            "vcpu": (it.get("cpu") or {}).get("number_of_cores"),
            "ram_gb": (it.get("memory") or {}).get("size_in_gigabytes"),
            "region": None,
            "available": None,
            "listing_url": "https://cloud.datacrunch.io/signin",
        }
        od = _num(it.get("price_per_hour"))
        if od and od > 0:
            r = dict(base)
            r.update({
                "price_total_hr": round(od, 4),
                "price_per_gpu_hr": round(od / n, 4),
                "pricing_type": "on-demand",
                "notes": "instance type %s" % it.get("instance_type"),
            })
            offers.append(r)
        sp = _num(it.get("spot_price"))
        if sp and sp > 0:
            r = dict(base)
            r.update({
                "price_total_hr": round(sp, 4),
                "price_per_gpu_hr": round(sp / n, 4),
                "pricing_type": "spot",
                "notes": "instance type %s, interruptible" % it.get("instance_type"),
            })
            offers.append(r)

    require(
        len(offers) >= MIN_OFFERS,
        "DataCrunch produced only %d priced rows from %d instance types "
        "(expected >= %d)." % (len(offers), len(data), MIN_OFFERS),
    )
    return offers, {"instance_types_without_gpus": len(skipped)}
