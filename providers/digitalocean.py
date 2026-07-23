"""DigitalOcean GPU Droplets. Parsed from the public pricing page.

Source: https://www.digitalocean.com/pricing/gpu-droplets

The page lists two sets of cards: a 12 month reserved set (which says "Contact
sales") and a self serve on demand set. Both quote /GPU/hour. We keep both but
tag them, because quoting a reserved rate as if you could click and get it would
be wrong.
"""

import re

from lib.common import ProviderError, fetch_text, require, strip_tags

KEY = "digitalocean"
NAME = "DigitalOcean"
HOMEPAGE = "https://www.digitalocean.com"
SOURCE = "https://www.digitalocean.com/pricing/gpu-droplets"
KIND = "provider"
COVERAGE = ("every card on the public GPU Droplet pricing page, including the 12 month "
            "reserved cards, which are tagged and kept out of the on-demand tables")
MIN_OFFERS = 8

CARD_RE = re.compile(
    r"\|([A-Za-z0-9][A-Za-z0-9 ™®+./-]{2,60}?)\|"
    r"\$([\d,]+\.\d{2})\|/GPU/hour\|"
    r"(On-Demand Price|12 Month Reserved Price\*?)\|"
)
SPEC_RE = re.compile(
    r"GPUs per Droplet\|(.*?)\|GPU Memory\|(\d+) GB\|"
    r"Droplet Memory\|([\d,]+) GiB\|Droplet vCPUs\|(\d+)\|"
)


def collect():
    text = strip_tags(fetch_text(SOURCE))
    require(
        "/GPU/hour" in text,
        "DigitalOcean page: no '/GPU/hour' text found at all. Layout changed.",
    )

    cards = list(CARD_RE.finditer(text))
    require(
        cards,
        "DigitalOcean page: found '/GPU/hour' but no price cards matched. "
        "Layout changed.",
    )

    offers = []
    for i, m in enumerate(cards):
        model = m.group(1).strip()
        price = float(m.group(2).replace(",", ""))
        label = m.group(3)
        ptype = "on-demand" if label.startswith("On-Demand") else "reserved-12mo"

        # Only read a spec block that belongs to THIS card. It must start
        # immediately after the price label and must not run past the next card,
        # otherwise a card with no specs would silently borrow its neighbour's.
        stop = cards[i + 1].start() if i + 1 < len(cards) else len(text)
        tail = text[m.end():stop]
        spec = SPEC_RE.search(tail)
        if spec and spec.start() != 0:
            spec = None
        vram = vcpu = ram = None
        counts = None
        if spec:
            counts = spec.group(1).strip()
            vram = int(spec.group(2))
            ram = int(spec.group(3).replace(",", ""))
            vcpu = int(spec.group(4))

        note = "self serve" if ptype == "on-demand" else "12 month commitment, contact sales"
        if counts:
            note += "; GPUs per droplet: %s" % counts
        offers.append({
            "provider": KEY,
            "gpu_model_raw": model,
            "gpu_count": 1,
            "vram_gb": vram,
            "price_total_hr": round(price, 4),
            "price_per_gpu_hr": round(price, 4),
            "pricing_type": ptype,
            "vcpu": vcpu,
            "ram_gb": ram,
            "region": None,
            "available": None,
            "notes": note,
            "listing_url": SOURCE,
        })

    on_demand = [o for o in offers if o["pricing_type"] == "on-demand"]
    require(
        len(on_demand) >= 5,
        "DigitalOcean produced only %d on-demand cards (expected >= 5)."
        % len(on_demand),
    )
    require(
        len(offers) >= MIN_OFFERS,
        "DigitalOcean produced only %d cards (expected >= %d)."
        % (len(offers), MIN_OFFERS),
    )

    notice = None
    nm = re.search(r"New on-demand pricing is coming on ([A-Z][a-z]+ \d+, \d{4})", text)
    if nm:
        notice = "DigitalOcean says new on-demand pricing takes effect %s" % nm.group(1)
    return offers, {"page_notice": notice}
