#!/usr/bin/env python3
"""Rewrite the generated tables in README.md from data/prices.json.

Everything between the BEGIN and END markers is replaced. Everything else in the
README is hand written and left alone.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(ROOT, "data", "prices.json")
STATUS = os.path.join(ROOT, "data", "status.json")
README = os.path.join(ROOT, "README.md")

BEGIN = "<!-- BEGIN GENERATED -->"
END = "<!-- END GENERATED -->"

# Models most people are actually shopping for, in the order they go in the doc.
# Where a chip ships in more than one form the form is part of the key, and each
# form gets its own table, because they are not the same product and should not
# be ranked against each other.
FEATURED = [
    "B200 180GB SXM", "B200 180GB (form unstated)",
    "H200 141GB SXM", "H200 141GB NVL", "H200 141GB (form unstated)",
    "H100 80GB SXM", "H100 80GB PCIe", "H100 94GB NVL",
    "A100 80GB SXM", "A100 80GB PCIe", "A100 40GB SXM", "A100 40GB PCIe",
    "RTX PRO 6000 Blackwell 96GB Server",
    "RTX PRO 6000 Blackwell 96GB Workstation",
    "RTX PRO 6000 Blackwell 96GB Max-Q",
    "RTX PRO 6000 Blackwell 96GB (form unstated)",
    "L40S 48GB", "RTX 6000 Ada 48GB",
    "RTX A6000 48GB", "A40 48GB", "RTX 5090 32GB", "RTX 4090 24GB",
    "RTX 3090 24GB", "L4 24GB", "A10 24GB",
    "V100 16GB SXM", "V100 16GB PCIe", "V100 16GB (form unstated)",
]

MAX_ROWS = 6

FORM_SOURCE_LABEL = {
    "provider": "the provider says so",
    "single-form-part": "only made in one form",
    "unknown": "nobody says",
}


def money(x):
    return "$%.4f" % x if x < 0.1 else "$%.3f" % x if x < 1 else "$%.2f" % x


def cheapest_rows(offers, key, pricing_types):
    rows = [o for o in offers
            if o["gpu_key"] == key
            and o["pricing_type"] in pricing_types
            and o.get("price_per_gpu_hr_usd") is not None]
    best = {}
    for o in rows:
        ident = (o["provider"], o["pricing_type"], o.get("gpu_form"),
                 o["gpu_model_raw"])
        # Cheapest wins. On a tie prefer the smallest config, since a 1 GPU
        # option is the one most readers can actually take.
        rank = (o["price_per_gpu_hr_usd"], o.get("gpu_count") or 0)
        if ident not in best or rank < (best[ident]["price_per_gpu_hr_usd"],
                                        best[ident].get("gpu_count") or 0):
            best[ident] = o
    out = sorted(best.values(),
                 key=lambda o: (o["price_per_gpu_hr_usd"], o.get("gpu_count") or 0))
    return out[:MAX_ROWS]


def table(offers, names, key, pricing_types):
    rows = cheapest_rows(offers, key, pricing_types)
    if not rows:
        return None
    lines = [
        "| $/GPU/hr | Provider | Listed as | Form | How we know the form | "
        "GPUs in config | Type |",
        "|---|---|---|---|---|---|---|",
    ]
    converted = False
    for o in rows:
        n = o.get("gpu_count")
        n = ("%g" % n) if isinstance(n, (int, float)) else "?"
        price = money(o["price_per_gpu_hr_usd"])
        if o.get("currency", "USD") != "USD":
            converted = True
            price += " *"
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            price,
            names.get(o["provider"], o["provider"]),
            o["gpu_model_raw"],
            o.get("gpu_form") or "not stated",
            FORM_SOURCE_LABEL.get(o.get("gpu_form_source"), "unknown"),
            n,
            o["pricing_type"],
        ))
    if converted:
        lines.append("")
        lines.append("\\* the provider quotes this one in euros, converted here "
                     "at the ECB daily rate")
    return "\n".join(lines)


def build(snapshot, status):
    offers = snapshot["offers"]
    provs = snapshot["providers"]
    names = {k: v["name"] for k, v in provs.items()}

    ts = snapshot["collected_at"].replace("+00:00", "Z")
    out = []
    out.append("Last checked **%s**. %d live offers from %d providers."
               % (ts, snapshot["offer_count"],
                  sum(1 for v in provs.values() if v["status"] != "error")))
    out.append("")

    fxi = snapshot.get("fx") or {}
    if fxi.get("eur_usd"):
        out.append("Euro prices converted at the ECB reference rate published %s, "
                   "1 EUR = %.4f USD." % (fxi["published"], fxi["eur_usd"]))
        out.append("")
    elif fxi.get("error"):
        out.append("> The ECB exchange rate feed was unreachable this run, so any "
                   "provider that quotes in euros is left out of the tables below.")
        out.append("")

    broken = [v["name"] for v in provs.values() if v["status"] == "error"]
    if broken:
        out.append("> Not included in this run because the collector could not "
                   "read them: %s. Rather than show you a stale number we show "
                   "nothing." % ", ".join(sorted(broken)))
        out.append("")
    flagged = (status or {}).get("anomalies") or []
    if flagged:
        out.append("> Price moves in this run that are large enough to be worth "
                   "a second look before you trust them:")
        for a in flagged[:10]:
            out.append(">   - %s" % a)
        out.append("")

    out.append("## Cheapest on-demand price per GPU")
    out.append("")
    out.append("One row per provider, cheapest configuration first. On-demand "
               "only, no spot and no reserved pricing. Prices exclude storage, "
               "bandwidth and tax unless noted in `data/prices.json`.")
    out.append("")

    for key in FEATURED:
        t = table(offers, names, key, ("on-demand",))
        if not t:
            continue
        out.append("### %s" % key)
        out.append("")
        out.append(t)
        out.append("")

    out.append("## Cheapest spot and interruptible price per GPU")
    out.append("")
    out.append("These can be reclaimed while your job is running. Do not compare "
               "them against the on-demand numbers above as if they were the "
               "same product.")
    out.append("")
    any_spot = False
    for key in FEATURED:
        t = table(offers, names, key, ("spot",))
        if not t:
            continue
        any_spot = True
        out.append("### %s (spot)" % key)
        out.append("")
        out.append(t)
        out.append("")
    if not any_spot:
        out.append("No spot pricing collected in this run.")
        out.append("")

    out.append("## Sources in this run")
    out.append("")
    out.append("| Provider | Offers | Models | Status | Where the numbers come from |")
    out.append("|---|---|---|---|---|")
    for k in sorted(provs):
        v = provs[k]
        note = v.get("error") or v["source"]
        out.append("| [%s](%s) | %s | %s | %s | %s |" % (
            v["name"], v["homepage"], v.get("offer_count", 0),
            v.get("models", 0), v["status"], note))
    out.append("")

    out.append("## What each source does and does not cover")
    out.append("")
    out.append("A missing GPU is usually a coverage limit, not a price of zero. "
               "This is what each collector actually asks for.")
    out.append("")
    out.append("| Provider | Covered |")
    out.append("|---|---|")
    for k in sorted(provs):
        v = provs[k]
        if v.get("coverage"):
            out.append("| %s | %s |" % (v["name"], v["coverage"]))
    out.append("")
    vast = ((status or {}).get("providers") or {}).get("vastai") or {}
    vmeta = vast.get("meta") or {}
    if vmeta.get("models_queried"):
        out.append("Vast.ai is the one that needs a number on it. This run asked "
                   "for %d GPU names, %d of which came from sampling the live "
                   "marketplace rather than from the built in list, and %d of "
                   "them had no verified stock. Anything Vast rents under a name "
                   "outside that set is not in this table."
                   % (len(vmeta["models_queried"]),
                      len(vmeta.get("models_discovered") or []),
                      len(vmeta.get("models_with_no_stock") or [])))
        out.append("")

    keys = sorted({o["gpu_key"] for o in offers})
    out.append("Full data for all %d GPU models we saw this run is in "
               "[`data/prices.json`](data/prices.json)." % len(keys))
    return "\n".join(out)


def main():
    snapshot = json.load(open(PRICES))
    status = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    body = build(snapshot, status)

    text = open(README).read()
    if BEGIN not in text or END not in text:
        print("README is missing the generated block markers", file=sys.stderr)
        return 1
    head = text.split(BEGIN)[0]
    tail = text.split(END, 1)[1]
    open(README, "w").write(head + BEGIN + "\n" + body + "\n" + END + tail)
    print("README updated (%d GPU models)" % len({o["gpu_key"] for o in snapshot["offers"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
