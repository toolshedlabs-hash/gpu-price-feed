"""Currency conversion, only where a provider genuinely prices in something
other than US dollars.

Right now that is Scaleway, which quotes euros ("Price (EUR/hour)" on its public
pricing page, and the instance API returns the same euro figures). Publishing a
euro number in a dollar column would be a lie of a few percent, and quietly
converting with a made up rate would be worse. So we take the European Central
Bank daily reference rate, record the exact rate and the date it was published
next to the data, and if the ECB feed is unreachable we set the dollar figure to
null and leave the provider out of the dollar tables for that run.
"""

import re
import xml.etree.ElementTree as ET

from lib.common import ProviderError, fetch_text

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
NS = {"ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}


def eur_to_usd():
    """Return (rate, date) from the ECB daily reference rates."""
    xml = fetch_text(ECB_URL)
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise ProviderError("ECB feed is not valid XML: %s" % e)

    date = None
    rate = None
    for cube in root.iter():
        tag = re.sub(r"\{.*\}", "", cube.tag)
        if tag != "Cube":
            continue
        if cube.get("time"):
            date = cube.get("time")
        if cube.get("currency") == "USD":
            rate = cube.get("rate")
    if not rate or not date:
        raise ProviderError("ECB feed had no USD reference rate")
    try:
        rate = float(rate)
    except ValueError:
        raise ProviderError("ECB USD rate %r is not a number" % rate)
    if not (0.5 < rate < 2.5):
        raise ProviderError("ECB USD rate %s is implausible" % rate)
    return rate, date
