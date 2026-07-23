"""Shared helpers for provider collectors. Standard library only."""

import gzip
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

UA = "gpu-price-feed/1.0 (+https://github.com/toolshedlabs-hash/gpu-price-feed)"
TIMEOUT = 60


class ProviderError(Exception):
    """Raised when a source cannot be fetched or parsed with confidence.

    Collectors must raise this instead of returning partial or guessed data.
    """


def _open(req):
    ctx = ssl.create_default_context()
    try:
        return urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
    except urllib.error.HTTPError as e:
        raise ProviderError("HTTP %s for %s" % (e.code, req.full_url))
    except Exception as e:
        raise ProviderError("fetch failed for %s: %s" % (req.full_url, e))


def fetch_text(url, headers=None):
    h = {"User-Agent": UA, "Accept-Encoding": "gzip", "Accept": "*/*"}
    if headers:
        h.update(headers)
    resp = _open(urllib.request.Request(url, headers=h))
    raw = resp.read()
    if resp.headers.get("Content-Encoding") == "gzip":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def fetch_json(url, headers=None):
    txt = fetch_text(url, headers)
    try:
        return json.loads(txt)
    except ValueError as e:
        raise ProviderError("non-JSON response from %s: %s" % (url, e))


def post_json(url, payload, headers=None):
    h = {"User-Agent": UA, "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    body = json.dumps(payload).encode()
    resp = _open(urllib.request.Request(url, data=body, headers=h, method="POST"))
    txt = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(txt)
    except ValueError as e:
        raise ProviderError("non-JSON response from %s: %s" % (url, e))


def require(cond, msg):
    if not cond:
        raise ProviderError(msg)


def strip_tags(html):
    import re

    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "|", t)
    t = t.replace("&amp;", "&").replace("&nbsp;", " ")
    t = t.replace("&#x27;", "'").replace("&quot;", '"')
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\|(\s*\|)+", "|", t)
    return t


def unescape_unicode(s):
    import re

    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
