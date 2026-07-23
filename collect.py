#!/usr/bin/env python3
"""Pull current GPU rental prices from every provider and write the data files.

Writes:
  data/prices.json               the current snapshot, one record per offer
  data/status.json               per provider health for this run
  data/history/v2/YYYY-MM.jsonl  append only, one line per run, cheapest per model

Schema 2 put the form factor into gpu_key, so keys from schema 1 do not line up
with keys from schema 2 and the two must not be concatenated into one series.
The schema 1 lines are frozen where they are, directly under data/history/, and
schema 2 lines go in data/history/v2/. Nothing already written is rewritten. See
data/history/README.md.

Exit codes:
  0  every provider collected cleanly
  2  at least one provider failed or tripped a sanity check
  3  every provider failed (the snapshot is not written)
"""

import datetime
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import fx, sanity
from lib.common import ProviderError
from lib.normalize import normalize
from providers import (akamai, datacrunch, digitalocean, lambdalabs, runpod,
                       scaleway, vastai, vultr)

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

PROVIDERS = [vastai, runpod, datacrunch, lambdalabs, digitalocean, scaleway,
             akamai, vultr]

SCHEMA_VERSION = 2
HISTORY = os.path.join(DATA, "history", "v%d" % SCHEMA_VERSION)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def enrich(offer, usd_per_eur):
    n = normalize(offer["gpu_model_raw"], offer.get("vram_gb"),
                  offer.get("gpu_model_alt"))
    offer["gpu_key"] = n["key"]
    offer["gpu_family"] = n["family"]
    offer["gpu_form"] = n["form"]
    offer["gpu_form_source"] = n["form_source"]
    offer["gpu_partition"] = n["partition"]
    offer["vram_gb"] = n["vram_gb"]
    offer["gpu_recognised"] = n["recognised"]

    cur = offer.setdefault("currency", "USD")
    if cur == "USD":
        offer["price_total_hr_usd"] = offer.get("price_total_hr")
        offer["price_per_gpu_hr_usd"] = offer.get("price_per_gpu_hr")
    elif cur == "EUR" and usd_per_eur:
        for src, dst in (("price_total_hr", "price_total_hr_usd"),
                         ("price_per_gpu_hr", "price_per_gpu_hr_usd")):
            v = offer.get(src)
            offer[dst] = round(v * usd_per_eur, 4) if v is not None else None
    else:
        offer["price_total_hr_usd"] = None
        offer["price_per_gpu_hr_usd"] = None
    return offer


def cheapest_map(offers):
    """{gpu_key: cheapest on-demand price per GPU hour in USD} for one provider."""
    out = {}
    for o in offers:
        if o.get("pricing_type") != "on-demand":
            continue
        p = o.get("price_per_gpu_hr_usd")
        if p is None:
            continue
        k = o["gpu_key"]
        if k not in out or p < out[k]:
            out[k] = p
    return out


def load_previous_cheapest():
    """Cheapest map per provider from the most recent history line, if any."""
    if not os.path.isdir(HISTORY):
        return {}
    files = sorted(f for f in os.listdir(HISTORY) if f.endswith(".jsonl"))
    if not files:
        return {}
    path = os.path.join(HISTORY, files[-1])
    last = None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                last = line
    if not last:
        return {}
    try:
        prev = json.loads(last)
    except ValueError:
        return {}
    # Never compare across schemas. The key space changed between them, so a
    # comparison would either match nothing or match the wrong thing.
    if prev.get("schema_version") != SCHEMA_VERSION:
        return {}
    return prev.get("cheapest", {})


def main():
    started = utcnow()
    previous = load_previous_cheapest()

    all_offers = []
    status = {}
    anomalies = []

    # Only Scaleway prices in a currency other than dollars today. If the ECB
    # feed is down we still publish, but the affected rows carry a null dollar
    # price instead of a number we made up.
    try:
        usd_per_eur, fx_date = fx.eur_to_usd()
        fx_info = {"eur_usd": usd_per_eur, "published": fx_date,
                   "source": fx.ECB_URL}
        print("fx    EUR/USD %.4f (ECB %s)" % (usd_per_eur, fx_date))
    except ProviderError as e:
        usd_per_eur, fx_info = None, {"error": str(e)}
        print("ERROR fx             %s" % e, file=sys.stderr)

    for mod in PROVIDERS:
        key = mod.KEY
        entry = {
            "name": mod.NAME,
            "homepage": mod.HOMEPAGE,
            "source": mod.SOURCE,
            "kind": mod.KIND,
            "coverage": mod.COVERAGE,
        }
        try:
            offers, meta = mod.collect()
            offers = [enrich(dict(o), usd_per_eur) for o in offers]

            problems = sanity.check_ranges(key, offers)
            if problems:
                raise ProviderError("; ".join(problems[:5]))

            cur = cheapest_map(offers)
            moved = sanity.check_against_previous(
                key, mod.KIND, cur, previous.get(key, {})
            )
            anomalies.extend(moved)

            all_offers.extend(offers)
            entry.update({
                "status": "ok" if not moved else "anomaly",
                "offer_count": len(offers),
                "models": len(cur),
                "meta": meta,
                "anomalies": moved,
            })
            print("ok    %-14s %4d offers, %3d models%s"
                  % (key, len(offers), len(cur),
                     "  [%d anomalies]" % len(moved) if moved else ""))
        except ProviderError as e:
            entry.update({"status": "error", "offer_count": 0, "error": str(e)})
            print("ERROR %-14s %s" % (key, e), file=sys.stderr)
        except Exception as e:  # noqa: BLE001 - a crash is still a provider failure
            entry.update({
                "status": "error",
                "offer_count": 0,
                "error": "unhandled %s: %s" % (type(e).__name__, e),
            })
            traceback.print_exc()
        status[key] = entry

    ok = [k for k, v in status.items() if v["status"] in ("ok", "anomaly")]
    if not ok:
        print("every provider failed, refusing to overwrite the snapshot",
              file=sys.stderr)
        os.makedirs(DATA, exist_ok=True)
        with open(os.path.join(DATA, "status.json"), "w") as fh:
            json.dump({"collected_at": started.isoformat(), "providers": status},
                      fh, indent=2, sort_keys=True)
            fh.write("\n")
        return 3

    all_offers.sort(key=lambda o: (
        o["gpu_key"], o.get("price_per_gpu_hr_usd") is None,
        o.get("price_per_gpu_hr_usd") or 0, o["provider"]))

    os.makedirs(HISTORY, exist_ok=True)
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "collected_at": started.isoformat(),
        "fx": fx_info,
        "providers": {k: {kk: vv for kk, vv in v.items() if kk != "meta"}
                      for k, v in status.items()},
        "offer_count": len(all_offers),
        "offers": all_offers,
    }
    with open(os.path.join(DATA, "prices.json"), "w") as fh:
        json.dump(snapshot, fh, indent=1, sort_keys=True)
        fh.write("\n")

    with open(os.path.join(DATA, "status.json"), "w") as fh:
        json.dump({
            "collected_at": started.isoformat(),
            "fx": fx_info,
            "providers": status,
            "anomalies": anomalies,
        }, fh, indent=2, sort_keys=True)
        fh.write("\n")

    by_provider = {}
    for o in all_offers:
        by_provider.setdefault(o["provider"], []).append(o)
    line = {
        "schema_version": SCHEMA_VERSION,
        "collected_at": started.isoformat(),
        "cheapest": {k: cheapest_map(v) for k, v in by_provider.items()},
    }
    hist_path = os.path.join(HISTORY, started.strftime("%Y-%m") + ".jsonl")
    with open(hist_path, "a") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")

    failed = [k for k, v in status.items() if v["status"] == "error"]
    print("\n%d offers from %d/%d providers" % (len(all_offers), len(ok),
                                                len(PROVIDERS)))
    if failed:
        print("failed: %s" % ", ".join(failed), file=sys.stderr)
    if anomalies:
        print("anomalies:", file=sys.stderr)
        for a in anomalies:
            print("  " + a, file=sys.stderr)
    return 2 if (failed or anomalies) else 0


if __name__ == "__main__":
    sys.exit(main())
