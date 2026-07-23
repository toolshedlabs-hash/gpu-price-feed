"""RunPod. Public GraphQL endpoint, no key required for the price catalog.

Endpoint: POST https://api.runpod.io/graphql

RunPod publishes two markets per GPU type:
  Secure Cloud    - vetted datacenters, higher price
  Community Cloud - third party hosts, lower price
plus spot ("interruptible") prices for each. We emit them as separate rows with
an explicit pricing_type so nobody reads a spot price as an on-demand price.

Prices are per GPU per hour. Storage and network egress are billed separately.
"""

from lib.common import ProviderError, post_json, require

KEY = "runpod"
NAME = "RunPod"
HOMEPAGE = "https://www.runpod.io"
SOURCE = "https://api.runpod.io/graphql"
KIND = "provider"
MIN_OFFERS = 25

QUERY = """query {
  gpuTypes {
    id
    displayName
    memoryInGb
    maxGpuCount
    securePrice
    communityPrice
    secureSpotPrice
    communitySpotPrice
    secureCloud
    communityCloud
    lowestPrice(input: {gpuCount: 1}) { stockStatus }
  }
}"""


def collect():
    d = post_json(SOURCE, {"query": QUERY})
    if "errors" in d:
        raise ProviderError("RunPod GraphQL errors: %s" % str(d["errors"])[:300])
    try:
        types = d["data"]["gpuTypes"]
    except (KeyError, TypeError):
        raise ProviderError("unexpected RunPod response shape: %s" % str(d)[:200])
    require(isinstance(types, list) and types, "RunPod returned no gpuTypes")

    offers = []
    no_price = []
    for t in types:
        raw = t.get("id")
        require(raw, "RunPod gpuType with no id")
        stock = (t.get("lowestPrice") or {}).get("stockStatus")
        rows = [
            ("securePrice", "on-demand", "secure cloud"),
            ("communityPrice", "on-demand", "community cloud"),
            ("secureSpotPrice", "spot", "secure cloud, interruptible"),
            ("communitySpotPrice", "spot", "community cloud, interruptible"),
        ]
        priced = False
        for field, ptype, note in rows:
            p = t.get(field)
            if p is None:
                continue
            p = float(p)
            if p <= 0:
                continue
            priced = True
            offers.append({
                "provider": KEY,
                "gpu_model_raw": raw,
                "gpu_count": 1,
                "vram_gb": t.get("memoryInGb"),
                "price_total_hr": round(p, 4),
                "price_per_gpu_hr": round(p, 4),
                "pricing_type": ptype,
                "vcpu": None,
                "ram_gb": None,
                "region": None,
                "available": None if stock is None else stock != "None",
                "notes": "%s; stock %s; up to %s GPUs" % (
                    note, stock or "unknown", t.get("maxGpuCount")),
                "listing_url": "https://www.runpod.io/console/deploy",
            })
        if not priced:
            no_price.append(raw)

    require(
        len(offers) >= MIN_OFFERS,
        "RunPod produced only %d priced rows from %d gpuTypes (expected >= %d). "
        "The GraphQL schema probably changed." % (len(offers), len(types), MIN_OFFERS),
    )
    return offers, {"gpu_types_with_no_price": no_price}
