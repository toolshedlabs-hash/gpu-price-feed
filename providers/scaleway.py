"""Scaleway. Public product catalog per availability zone, no key required.

Endpoint: GET https://api.scaleway.com/instance/v1/zones/<zone>/products/servers

Scaleway prices differ by zone, so we query every zone that currently offers GPU
instances and keep the zone on each row. hourly_price is for the whole instance.
Block storage is billed separately.

IMPORTANT: this API returns EUROS, not dollars, and it does not label the
currency. Scaleway's public pricing page column header reads "Price (EUR/hour)"
and the figures line up exactly (L4-1-24G is 0.7875 from the API and EUR 0.79 on
the page). Every row here is tagged currency EUR and converted to dollars at the
ECB daily reference rate, with the rate recorded in the snapshot.
"""

from lib.common import ProviderError, fetch_json, require

KEY = "scaleway"
NAME = "Scaleway"
HOMEPAGE = "https://www.scaleway.com"
SOURCE = "https://api.scaleway.com/instance/v1/zones/{zone}/products/servers"
KIND = "provider"
MIN_OFFERS = 5

ZONES = ["fr-par-1", "fr-par-2", "fr-par-3", "nl-ams-1", "nl-ams-2", "nl-ams-3",
         "pl-waw-1", "pl-waw-2", "pl-waw-3"]

GIB = 1024 ** 3


def collect():
    offers = []
    zones_ok = []
    zones_failed = []
    for zone in ZONES:
        try:
            data = fetch_json(SOURCE.format(zone=zone))
        except ProviderError as e:
            zones_failed.append("%s: %s" % (zone, e))
            continue
        servers = data.get("servers")
        if not isinstance(servers, dict):
            zones_failed.append("%s: no servers dict" % zone)
            continue
        zones_ok.append(zone)
        for name, s in servers.items():
            n = s.get("gpu") or 0
            if not n:
                continue
            info = s.get("gpu_info") or {}
            model = info.get("gpu_name") or name
            price = s.get("hourly_price")
            if price is None:
                raise ProviderError(
                    "Scaleway %s/%s has a GPU but no hourly_price" % (zone, name))
            price = float(price)
            if price <= 0:
                continue
            # gpu_memory is PER GPU here, not the instance total. Verified
            # against the instance naming: L4-8-24G reports 24 GiB, and an L4
            # has 24 GB. Dividing by the GPU count would be wrong.
            vram = info.get("gpu_memory")
            vram_per = int(round(vram / GIB)) if vram else None
            offers.append({
                "provider": KEY,
                "gpu_model_raw": model,
                "gpu_count": int(n),
                "vram_gb": vram_per,
                "price_total_hr": round(price, 4),
                "price_per_gpu_hr": round(price / n, 4),
                "pricing_type": "on-demand",
                "currency": "EUR",
                "vcpu": s.get("ncpus"),
                "ram_gb": int(round(s["ram"] / GIB)) if s.get("ram") else None,
                "region": zone,
                "available": None,
                "notes": "instance type %s" % name,
                "listing_url": "https://www.scaleway.com/en/gpu-instances/",
            })

    require(zones_ok, "Scaleway: every zone request failed: %s" % zones_failed)
    require(
        len(offers) >= MIN_OFFERS,
        "Scaleway produced only %d GPU rows across %d zones (expected >= %d)."
        % (len(offers), len(zones_ok), MIN_OFFERS),
    )
    return offers, {"zones_ok": zones_ok, "zones_failed": zones_failed}
