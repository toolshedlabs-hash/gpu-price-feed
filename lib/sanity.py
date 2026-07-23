"""Sanity checks. These exist so a broken parser fails loudly instead of quietly
publishing a number that is off by a factor of ten."""

# Nothing real rents outside this band. A parser that grabs the wrong element on a
# page almost always lands outside it (a monthly figure, a GB count, a phone
# number), so this catches the common failure.
MIN_PRICE = 0.005
MAX_PRICE = 200.0

# Fixed catalog providers publish a price list. Real moves are small and rare.
# Marketplaces genuinely swing, so they get a looser band and a warning instead.
FIXED_MAX_RATIO = 2.0
MARKET_MAX_RATIO = 5.0


def check_ranges(provider_key, offers):
    """Raise on any price outside the plausible band."""
    problems = []
    for o in offers:
        for field in ("price_total_hr_usd", "price_per_gpu_hr_usd"):
            p = o.get(field)
            if p is None:
                continue
            if not (MIN_PRICE <= p <= MAX_PRICE):
                problems.append(
                    "%s %s %s = %s is outside $%.3f..$%.0f per hour"
                    % (provider_key, o.get("gpu_model_raw"), field, p,
                       MIN_PRICE, MAX_PRICE)
                )
    return problems


def check_against_previous(provider_key, kind, current_min, previous_min):
    """Compare this run's cheapest price per model against the last run's.

    current_min / previous_min are {canonical_key: price}. Returns a list of
    human readable anomaly strings. A big move is not proof of a bug, but it is
    always worth a human look, so we surface it and let the job go red.
    """
    limit = FIXED_MAX_RATIO if kind != "marketplace" else MARKET_MAX_RATIO
    out = []
    for key, now in sorted(current_min.items()):
        before = previous_min.get(key)
        if not before or not now:
            continue
        ratio = now / before if now > before else before / now
        if ratio > limit:
            out.append(
                "%s %s moved from $%.4f to $%.4f per GPU hour (%.1fx, limit %.1fx)"
                % (provider_key, key, before, now, ratio, limit)
            )
    return out
