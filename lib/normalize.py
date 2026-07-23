"""GPU model name normalization.

Every provider spells the same chip differently. This maps raw provider strings to
a canonical family, a VRAM size and a form factor, so prices can be compared
without silently merging things that are not the same product.

Three rules that matter for accuracy:

  1. We never merge different VRAM sizes. An A100 40GB and an A100 80GB are
     different products and get different canonical keys.
  2. For families that ship in more than one non substitutable form (H100 SXM vs
     H100 PCIe, and so on) the form is part of the canonical key. A cheapest match
     on the key can then never hand you a PCIe part when you asked for SXM.
  3. We never guess a form. It comes from what the provider itself publishes, or
     from the fact that the part only exists in one form. When neither applies the
     key says `(form unstated)` and stays separate from every known form, so an
     unstated part can never be substituted for a specific one.
"""

import re

# family regex -> (canonical family, default vram GB or None, single form or None)
#
# The third column is only filled in for parts that the vendor ships in exactly
# one form, so there is nothing to disambiguate. It is a fact about the part, not
# a guess about the listing. Anything sold in several forms is left None here and
# has to be resolved from the provider's own string.
#
# Ordered. First match wins, so put the specific patterns first.
_RULES = [
    (r"\bGB300\b", "GB300", 288, "SXM"),
    (r"\bGB200\b", "GB200", 192, "SXM"),
    (r"\bB300\b", "B300", 288, None),
    (r"\bB200\b", "B200", 180, None),
    (r"\bGH200\b", "GH200", 96, None),
    (r"\bH200\s*NVL\b", "H200", 141, "NVL"),
    (r"\bH200\b", "H200", 141, None),
    (r"\bH100\s*NVL\b", "H100", 94, "NVL"),
    (r"\bH100\b", "H100", 80, None),
    (r"\bH800\b", "H800", 80, None),
    (r"\bA100\b", "A100", None, None),
    (r"\bA800\b", "A800", 80, None),
    (r"\bMI355X?\b", "MI355X", 288, "OAM"),
    (r"\bMI350X?\b", "MI350X", 288, "OAM"),
    (r"\bMI325X?\b", "MI325X", 256, "OAM"),
    (r"\bMI300X?\b", "MI300X", 192, "OAM"),
    (r"\bMI210\b", "MI210", 64, "PCIe"),
    (r"\bL40S\b", "L40S", 48, "PCIe"),
    (r"\bL40\b", "L40", 48, "PCIe"),
    (r"\bL4\b", "L4", 24, "PCIe"),
    (r"\bA10G\b", "A10G", 24, "PCIe"),
    (r"\bA100X\b", "A100X", 80, None),
    (r"\bA40\b", "A40", 48, "PCIe"),
    # An A16 board carries four independent 16 GB GPUs. Providers sell them one
    # GPU at a time, so 16 GB is the per GPU number a buyer sees.
    (r"\bA16\b", "A16", 16, "PCIe"),
    (r"\bA10\b", "A10", 24, "PCIe"),
    (r"\bA2\b", "A2", 16, "PCIe"),
    (r"\bRTX\s*PRO\s*6000\b", "RTX PRO 6000 Blackwell", 96, None),
    (r"\bRTX\s*PRO\s*5000\b", "RTX PRO 5000 Blackwell", 48, None),
    (r"\bRTX\s*PRO\s*4500\b", "RTX PRO 4500 Blackwell", 32, None),
    (r"\bRTX\s*PRO\s*4000\b", "RTX PRO 4000 Blackwell", 24, None),
    (r"\bRTX\s*4000\s*SFF\s*Ada\b", "RTX 4000 SFF Ada", 20, "PCIe"),
    (r"\bRTX\s*6000\s*Ada\b|\b6000\s*Ada\b", "RTX 6000 Ada", 48, "PCIe"),
    (r"\bRTX\s*5880\s*Ada\b|\b5880\s*Ada\b", "RTX 5880 Ada", 48, "PCIe"),
    (r"\bRTX\s*5000\s*Ada\b|\b5000\s*Ada\b", "RTX 5000 Ada", 32, "PCIe"),
    (r"\bRTX\s*4500\s*Ada\b|\b4500\s*Ada\b", "RTX 4500 Ada", 24, "PCIe"),
    (r"\bRTX\s*4000\s*Ada\b|\b4000\s*Ada\b|\bRTX4000\s*Ada\b", "RTX 4000 Ada", 20, "PCIe"),
    (r"\bRTX\s*2000\s*Ada\b|\b2000\s*Ada\b", "RTX 2000 Ada", 16, None),
    (r"\bRTX\s*A6000\b|\bA6000\b", "RTX A6000", 48, "PCIe"),
    (r"\bRTX\s*A5000\b|\bA5000\b", "RTX A5000", 24, "PCIe"),
    (r"\bRTX\s*A4500\b|\bA4500\b", "RTX A4500", 20, "PCIe"),
    (r"\bRTX\s*A4000\b|\bA4000\b", "RTX A4000", 16, "PCIe"),
    (r"\bRTX\s*A2000\b|\bA2000\b", "RTX A2000", 12, None),
    (r"\bQuadro\s*RTX\s*8000\b|\bQ\s*RTX\s*8000\b|\bRTX\s*8000\b",
     "Quadro RTX 8000", 48, "PCIe"),
    (r"\bQuadro\s*RTX\s*6000\b|\bRTX6000\b|\bRTX\s*6000\b",
     "Quadro RTX 6000", 24, "PCIe"),
    (r"\bQuadro\s*P4000\b|\bP4000\b", "Quadro P4000", 8, "PCIe"),
    (r"\bRTX\s*5090\b", "RTX 5090", 32, None),
    (r"\bRTX\s*5080\b", "RTX 5080", 16, None),
    (r"\bRTX\s*5070\s*Ti\b", "RTX 5070 Ti", 16, None),
    (r"\bRTX\s*5070\b", "RTX 5070", 12, None),
    (r"\bRTX\s*5060\s*Ti\b", "RTX 5060 Ti", 16, None),
    (r"\bRTX\s*5060\b", "RTX 5060", 8, None),
    (r"\bRTX\s*4090\b", "RTX 4090", 24, None),
    (r"\bRTX\s*4080\s*SUPER\b|\bRTX\s*4080S\b", "RTX 4080 SUPER", 16, None),
    (r"\bRTX\s*4080\b", "RTX 4080", 16, None),
    (r"\bRTX\s*4070\s*Ti\s*SUPER\b|\bRTX\s*4070S\s*Ti\b",
     "RTX 4070 Ti SUPER", 16, None),
    (r"\bRTX\s*4070\s*SUPER\b|\bRTX\s*4070S\b", "RTX 4070 SUPER", 12, None),
    (r"\bRTX\s*4070\s*Ti\b", "RTX 4070 Ti", 12, None),
    (r"\bRTX\s*4070\b", "RTX 4070", 12, None),
    (r"\bRTX\s*4060\s*Ti\b", "RTX 4060 Ti", 16, None),
    (r"\bRTX\s*4060\b", "RTX 4060", 8, None),
    (r"\bRTX\s*3090\s*Ti\b", "RTX 3090 Ti", 24, None),
    (r"\bRTX\s*3090\b", "RTX 3090", 24, None),
    (r"\bRTX\s*3080\s*Ti\b", "RTX 3080 Ti", 12, None),
    (r"\bRTX\s*3080\b", "RTX 3080", 10, None),
    (r"\bRTX\s*3070\s*Ti\b", "RTX 3070 Ti", 8, None),
    (r"\bRTX\s*3070\b", "RTX 3070", 8, None),
    (r"\bRTX\s*3060\s*Ti\b", "RTX 3060 Ti", 8, None),
    (r"\bRTX\s*3060\b", "RTX 3060", 12, None),
    (r"\bRTX\s*2080\s*Ti\b", "RTX 2080 Ti", 11, None),
    (r"\bRTX\s*2070\b", "RTX 2070", 8, None),
    (r"\bTitan\s*RTX\b", "Titan RTX", 24, None),
    (r"\bTitan\s*Xp\b", "Titan Xp", 12, None),
    (r"\bGTX\s*1660\s*Ti\b", "GTX 1660 Ti", 6, None),
    (r"\bGTX\s*1660\s*S\b|\bGTX\s*1660\s*SUPER\b", "GTX 1660 SUPER", 6, None),
    (r"\bGTX\s*1660\b", "GTX 1660", 6, None),
    (r"\bGTX\s*1080\s*Ti\b", "GTX 1080 Ti", 11, None),
    (r"\bGTX\s*1080\b", "GTX 1080", 8, None),
    (r"\bGTX\s*1070\s*Ti\b", "GTX 1070 Ti", 8, None),
    (r"\bGTX\s*1070\b", "GTX 1070", 8, None),
    (r"\bGTX\s*1060\b", "GTX 1060", 6, None),
    (r"\bGTX\s*1050\s*Ti\b", "GTX 1050 Ti", 4, None),
    (r"\bV100\b", "V100", None, None),
    (r"\bP100\b", "P100", 16, None),
    (r"\bT4\b", "T4", 16, "PCIe"),
    (r"\bP40\b", "P40", 24, "PCIe"),
    (r"\bP4\b", "P4", 8, "PCIe"),
]

# Families that the vendor ships in several forms which are NOT substitutable for
# each other. For these the form goes into the canonical key, and a listing that
# does not state its form gets its own key rather than being lumped in with a
# known one.
FORM_IN_KEY = frozenset([
    "H100", "H200", "H800", "A100", "A800",
    "B200", "B300", "GB200", "GB300",
    "V100", "P100",
    "RTX PRO 6000 Blackwell",
])

# Tokens a provider can put in its own listing name that settle the form. Checked
# in order, first hit wins, so the specific ones come first.
_FORM_PATTERNS = [
    (r"\bMAX\s*Q\b", "Max-Q"),
    (r"\bSXM\d?\b", "SXM"),
    (r"\bHGX\b", "SXM"),
    (r"\bNVL\b", "NVL"),
    (r"\bPCIE\b|\bPCIe\b", "PCIe"),
    (r"\bOAM\b", "OAM"),
    (r"\bMOBILE\b|\bLAPTOP\b", "Mobile"),
]

# Board variants that only exist inside one family, so the token is only trusted
# when we are already looking at that family. "Server" and "Workstation" are the
# names NVIDIA gives two builds of the same RTX PRO chip.
#
# The two letter forms are Vast.ai's shorthand, documented on Vast's own pricing
# pages, so this is the provider stating the variant rather than us inferring it:
#   https://vast.ai/pricing/gpu/RTX-PRO-6000-S  "RTX PRO 6000 Blackwell Server Edition"
#   https://vast.ai/pricing/gpu/RTX-PRO-6000-WS "RTX PRO 6000 Blackwell Workstation Edition"
_RTX_PRO_VARIANTS = [
    (r"\bMAX\s*Q\b", "Max-Q"),
    (r"\bSERVER\b", "Server"),
    (r"\bWORKSTATION\b", "Workstation"),
    (r"\bWS\b", "Workstation"),
    (r"\bS\b", "Server"),
]
_FAMILY_SHORTHAND = {
    "RTX PRO 6000 Blackwell": _RTX_PRO_VARIANTS,
    "RTX PRO 5000 Blackwell": _RTX_PRO_VARIANTS,
    "RTX PRO 4500 Blackwell": _RTX_PRO_VARIANTS,
    "RTX PRO 4000 Blackwell": _RTX_PRO_VARIANTS,
}

_MIG_RE = re.compile(r"\bMIG\s*(\d+g\.\d+gb)\b", re.I)

_NOISE = re.compile(
    r"\b(NVIDIA|AMD|GeForce|Tesla|Instinct|Corporation|Generation|GPU|Edition)\b",
    re.I,
)

# Advertised VRAM capacities, in GB. Real listings land near one of these rather
# than exactly on it, for two reasons that both have a direction:
#   - what a card reports as usable is at or below what it is sold as. ECC on a
#     GDDR6 board costs 6.25 percent, which is why an L40S reports 46068 MiB and
#     is still sold as a 48 GB card.
#   - a provider sometimes rounds the advertised figure up by a hair.
# So we snap up to 8 percent and down to 2 percent, and otherwise leave the
# number exactly as reported rather than force it into a bucket.
_CAPACITIES = [3, 4, 6, 8, 10, 11, 12, 16, 20, 24, 32, 40, 48, 64, 80, 94, 96,
               141, 180, 192, 256, 288]
_SNAP_UP = 0.08
_SNAP_DOWN = 0.02


def snap_vram(gb):
    """Snap a reported VRAM figure onto the capacity the part is sold as."""
    if gb is None:
        return None
    best = None
    for t in _CAPACITIES:
        if t >= gb:
            slack = (t - gb) / float(t)
            if slack > _SNAP_UP:
                continue
        else:
            slack = (gb - t) / float(t)
            if slack > _SNAP_DOWN:
                continue
        if best is None or slack < best[0]:
            best = (slack, t)
    return best[1] if best else int(round(gb))


def round_vram(mb):
    """Convert a provider's VRAM in MiB to the capacity the card is sold as.

    24564 -> 24, 81920 -> 80, 143771 -> 141, 46068 -> 48 (ECC is on), 97887 -> 96.
    """
    if not mb:
        return None
    return snap_vram(mb / 1024.0)


def _clean(raw):
    s = raw.replace("™", " ").replace("®", " ")
    s = s.replace("_", " ").replace("-", " ")
    s = _NOISE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _vram_from_text(s):
    m = re.search(r"(\d{2,4})\s*GB", s, re.I)
    if m:
        v = int(m.group(1))
        if 4 <= v <= 1024:
            return v
    return None


def _detect_form(text, family):
    for pat, f in _FORM_PATTERNS:
        if re.search(pat, text, re.I):
            return f
    for pat, f in _FAMILY_SHORTHAND.get(family, []):
        if re.search(pat, text, re.I):
            return f
    return None


def normalize(raw_name, vram_gb=None, alt_name=None):
    """Work out the canonical identity of one listing.

    raw_name is the provider's own string for the part. alt_name is a second
    string from the same provider for the same part when there is one (RunPod
    publishes both an id and a displayName, and only the displayName says SXM).

    Returns a dict:
      key         what the comparison tables group on, e.g. "H100 80GB SXM"
      family      "H100"
      vram_gb     80
      form        "SXM", "PCIe", "NVL", "OAM", "Server", "Workstation", "Max-Q",
                  "Mobile", or None
      form_source "provider"          the provider's own listing says so
                  "single-form-part"  the part is only made in one form
                  "unknown"           nobody said, and the part has several forms
      partition   "MIG 1g.24gb" when the listing is a slice of a card, else None
      recognised  False when we do not know the chip. Those keep their raw name as
                  the key and stay out of the headline tables rather than being
                  forced into a bucket they may not belong in.
    """
    joined = " ".join(x for x in (raw_name, alt_name) if x)
    s = _clean(joined)

    fam = None
    default_vram = None
    single_form = None
    for pat, family, dv, sf in _RULES:
        if re.search(pat, s, re.I):
            fam = family
            default_vram = dv
            single_form = sf
            break

    stated = _detect_form(s, fam)
    if stated:
        form, form_source = stated, "provider"
    elif single_form:
        form, form_source = single_form, "single-form-part"
    else:
        form, form_source = None, "unknown"

    mig = _MIG_RE.search(joined)
    partition = "MIG " + mig.group(1).lower() if mig else None

    v = snap_vram(vram_gb or _vram_from_text(joined) or default_vram)

    if fam is None:
        return {
            "key": raw_name.strip(),
            "family": raw_name.strip(),
            "vram_gb": v,
            "form": form,
            "form_source": form_source,
            "partition": partition,
            "recognised": False,
        }

    parts = [fam]
    if v:
        parts.append("%sGB" % v)
    if fam in FORM_IN_KEY:
        parts.append(form if form else "(form unstated)")
    elif form in ("Max-Q", "Mobile"):
        # Not a family we split by form, but these two are slow enough versions of
        # the same chip that merging them with the full fat part would mislead.
        parts.append(form)
    if partition:
        parts.append("MIG")

    return {
        "key": " ".join(parts),
        "family": fam,
        "vram_gb": v,
        "form": form,
        "form_source": form_source,
        "partition": partition,
        "recognised": True,
    }
