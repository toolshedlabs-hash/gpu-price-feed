"""RunPod. Public GraphQL endpoint, no key required for the price catalog.

Endpoint: POST https://api.runpod.io/graphql

RunPod publishes two markets per GPU type:
  Secure Cloud    - vetted datacenters, higher price
  Community Cloud - third party hosts, lower price
plus spot ("interruptible") prices for each. We emit them as separate rows with
an explicit pricing_type so nobody reads a spot price as an on-demand price.

A price is only published when RunPod's own `secureCloud` / `communityCloud` flag
says the card is actually offered in that market. The API keeps stale numbers on
file for markets that are closed, and one of them ($0.50 for an H200 NVL on a
community cloud RunPod flags false) would otherwise have topped a table with a
price nobody can buy.

Prices are per GPU per hour. Storage and network egress are billed separately.
"""

from lib.common import ProviderError, post_json, require

KEY = "runpod"
NAME = "RunPod"
HOMEPAGE = "https://www.runpod.io"
SOURCE = "https://api.runpod.io/graphql"
KIND = "provider"
MIN_OFFERS = 25
COVERAGE = ("every GPU type in RunPod's public catalog, on-demand and spot, but "
            "only for the markets RunPod flags as actually offering that card")

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
    suppressed = []
    for t in types:
        raw = t.get("id")
        require(raw, "RunPod gpuType with no id")
        stock = (t.get("lowestPrice") or {}).get("stockStatus")
        rows = [
            ("securePrice", "on-demand", "secure cloud", "secureCloud"),
            ("communityPrice", "on-demand", "community cloud", "communityCloud"),
            ("secureSpotPrice", "spot", "secure cloud, interruptible", "secureCloud"),
            ("communitySpotPrice", "spot", "community cloud, interruptible",
             "communityCloud"),
        ]
        priced = False
        for field, ptype, note, market_flag in rows:
            p = t.get(field)
            if p is None:
                continue
            # RunPod keeps a price on file for markets it does not currently
            # offer the card in, and those numbers are stale. H200 NVL came back
            # at a community price of $0.50 with communityCloud false, against
            # $3.79 secure, and RunPod's own pricing page lists no community
            # H200 NVL at all. Publishing that would have been the cheapest H200
            # NVL in the table and unbuyable, so we drop any price whose market
            # RunPod does not flag as open.
            if t.get(market_flag) is not True:
                suppressed.append("%s %s (%s is %r)"
                                  % (raw, field, market_flag, t.get(market_flag)))
                continue
            p = float(p)
            if p <= 0:
                continue
            priced = True
            offers.append({
                "provider": KEY,
                "gpu_model_raw": raw,
                # RunPod publishes two names per type. The id is the nvidia-smi
                # product string and the displayName is the console label, and
                # they carry different information: id "NVIDIA H100 80GB HBM3"
                # does not say SXM, displayName "H100 SXM" does. We keep both and
                # let the normalizer read the form out of either.
                "gpu_model_alt": t.get("displayName"),
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
    return offers, {
        "gpu_types_with_no_price": no_price,
        "prices_dropped_market_not_offered": suppressed,
    }
