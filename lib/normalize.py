"""GPU model name normalization.

Every provider spells the same chip differently. This maps raw provider strings to
a canonical family plus a form factor, so prices can be compared without silently
merging things that are not the same product.

Two rules that matter for accuracy:
  1. We never merge different VRAM sizes. An A100 40GB and an A100 80GB are
     different products and get different canonical keys.
  2. Form factor (SXM / PCIe / NVL) is kept as a separate field, not folded into
     the key. Some providers do not state it. Guessing would be worse than a blank.
"""

import re

# family regex -> (canonical family, default vram GB or None, default form or None)
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
    (r"\bMI355X?\b", "MI355X", 288, None),
    (r"\bMI350X?\b", "MI350X", 288, None),
    (r"\bMI325X?\b", "MI325X", 256, None),
    (r"\bMI300X?\b", "MI300X", 192, None),
    (r"\bMI210\b", "MI210", 64, None),
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
    (r"\bRTX\s*4000\s*SFF\s*Ada\b", "RTX 4000 SFF Ada", 20, None),
    (r"\bRTX\s*6000\s*Ada\b|\b6000\s*Ada\b", "RTX 6000 Ada", 48, None),
    (r"\bRTX\s*5000\s*Ada\b|\b5000\s*Ada\b", "RTX 5000 Ada", 32, None),
    (r"\bRTX\s*4500\s*Ada\b|\b4500\s*Ada\b", "RTX 4500 Ada", 24, None),
    (r"\bRTX\s*4000\s*Ada\b|\b4000\s*Ada\b|\bRTX4000\s*Ada\b", "RTX 4000 Ada", 20, None),
    (r"\bRTX\s*2000\s*Ada\b|\b2000\s*Ada\b", "RTX 2000 Ada", 16, None),
    (r"\bRTX\s*A6000\b|\bA6000\b", "RTX A6000", 48, None),
    (r"\bRTX\s*A5000\b|\bA5000\b", "RTX A5000", 24, None),
    (r"\bRTX\s*A4500\b|\bA4500\b", "RTX A4500", 20, None),
    (r"\bRTX\s*A4000\b|\bA4000\b", "RTX A4000", 16, None),
    (r"\bRTX\s*A2000\b|\bA2000\b", "RTX A2000", 12, None),
    (r"\bQuadro\s*RTX\s*8000\b|\bRTX\s*8000\b", "Quadro RTX 8000", 48, None),
    (r"\bQuadro\s*RTX\s*6000\b|\bRTX6000\b|\bRTX\s*6000\b", "Quadro RTX 6000", 24, None),
    (r"\bRTX\s*5090\b", "RTX 5090", 32, None),
    (r"\bRTX\s*5080\b", "RTX 5080", 16, None),
    (r"\bRTX\s*5070\s*Ti\b", "RTX 5070 Ti", 16, None),
    (r"\bRTX\s*5060\s*Ti\b", "RTX 5060 Ti", 16, None),
    (r"\bRTX\s*4090\b", "RTX 4090", 24, None),
    (r"\bRTX\s*4080\s*SUPER\b", "RTX 4080 SUPER", 16, None),
    (r"\bRTX\s*4080\b", "RTX 4080", 16, None),
    (r"\bRTX\s*4070\s*Ti\s*SUPER\b", "RTX 4070 Ti SUPER", 16, None),
    (r"\bRTX\s*4070\s*Ti\b", "RTX 4070 Ti", 12, None),
    (r"\bRTX\s*4070\b", "RTX 4070", 12, None),
    (r"\bRTX\s*4060\s*Ti\b", "RTX 4060 Ti", 16, None),
    (r"\bRTX\s*4060\b", "RTX 4060", 8, None),
    (r"\bRTX\s*3090\s*Ti\b", "RTX 3090 Ti", 24, None),
    (r"\bRTX\s*3090\b", "RTX 3090", 24, None),
    (r"\bRTX\s*3080\s*Ti\b", "RTX 3080 Ti", 12, None),
    (r"\bRTX\s*3080\b", "RTX 3080", 10, None),
    (r"\bRTX\s*3070\b", "RTX 3070", 8, None),
    (r"\bRTX\s*3060\b", "RTX 3060", 12, None),
    (r"\bRTX\s*2080\s*Ti\b", "RTX 2080 Ti", 11, None),
    (r"\bTitan\s*RTX\b", "Titan RTX", 24, None),
    (r"\bGTX\s*1080\s*Ti\b", "GTX 1080 Ti", 11, None),
    (r"\bGTX\s*1080\b", "GTX 1080", 8, None),
    (r"\bGTX\s*1070\s*Ti\b", "GTX 1070 Ti", 8, None),
    (r"\bGTX\s*1060\b", "GTX 1060", 6, None),
    (r"\bGTX\s*1050\s*Ti\b", "GTX 1050 Ti", 4, None),
    (r"\bV100\b", "V100", None, None),
    (r"\bP100\b", "P100", 16, None),
    (r"\bT4\b", "T4", 16, "PCIe"),
    (r"\bP40\b", "P40", 24, None),
    (r"\bP4\b", "P4", 8, None),
]

_FORM_PATTERNS = [
    (r"\bSXM6\b", "SXM"),
    (r"\bSXM5\b", "SXM"),
    (r"\bSXM4\b", "SXM"),
    (r"\bSXM\b", "SXM"),
    (r"\bHGX\b", "SXM"),
    (r"\bNVL\b", "NVL"),
    (r"\bPCIE\b|\bPCIe\b", "PCIe"),
    (r"\bOAM\b", "OAM"),
]

_NOISE = re.compile(
    r"\b(NVIDIA|AMD|GeForce|Tesla|Instinct|Corporation|Generation|GPU)\b", re.I
)


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


def normalize(raw_name, vram_gb=None):
    """Return (canonical_key, family, form, vram_gb, matched).

    canonical_key is what the comparison tables group on, e.g. "H100 80GB".
    matched is False when we do not recognise the chip. Unrecognised chips keep
    their raw name and are excluded from the headline comparison tables rather
    than being force-fitted into a bucket they may not belong in.
    """
    s = _clean(raw_name)
    form = None
    for pat, f in _FORM_PATTERNS:
        if re.search(pat, s, re.I):
            form = f
            break

    fam = None
    default_vram = None
    default_form = None
    for pat, family, dv, df in _RULES:
        if re.search(pat, s, re.I):
            fam = family
            default_vram = dv
            default_form = df
            break

    text_vram = _vram_from_text(raw_name)
    v = vram_gb or text_vram or default_vram
    if form is None:
        form = default_form

    if fam is None:
        return (raw_name.strip(), raw_name.strip(), form, v, False)

    key = "%s %sGB" % (fam, v) if v else fam
    return (key, fam, form, v, True)


def round_vram(mb):
    """Convert a provider's VRAM in MB to the marketing GB number.

    24564 MB -> 24, 81920 -> 80, 143771 -> 141. Providers report the real usable
    bytes; buyers shop by the round number.
    """
    if not mb:
        return None
    gb = mb / 1024.0
    for target in (4, 6, 8, 10, 11, 12, 16, 20, 24, 32, 40, 48, 64, 80, 94, 96,
                   141, 144, 180, 192, 256, 288):
        if abs(gb - target) / target < 0.06:
            return target
    return int(round(gb))
