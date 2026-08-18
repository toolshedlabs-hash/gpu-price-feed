# gpu-price-feed

Live GPU rental prices from eight cloud providers, refreshed daily, in machine
readable JSON with a full append only history.

There are plenty of GPU price pages. Most of them are hand maintained, undated,
and quietly wrong within a week. This one is a script. It reads each provider's
own API or pricing page every day, normalizes the GPU names so an H100 on one
provider lines up with an H100 on another, and commits the result. Every past
snapshot stays in the repo, so you can check whether the ranking actually
followed the prices.

If a parser breaks, the run fails and that provider is dropped from the table.
It never falls back to yesterday's number and pretends it is today's.

## Use it

Latest snapshot, always at the same URL:

```
https://raw.githubusercontent.com/toolshedlabs-hash/gpu-price-feed/main/data/prices.json
```

```bash
curl -s https://raw.githubusercontent.com/toolshedlabs-hash/gpu-price-feed/main/data/prices.json \
  | jq -r '.offers[] | select(.gpu_key=="H100 80GB SXM" and .pricing_type=="on-demand")
           | [.price_per_gpu_hr_usd, .provider, .gpu_model_raw, .gpu_form] | @tsv' \
  | sort -n | head
```

One offer, exactly as it appears in the file:

```json
{
  "provider": "datacrunch",
  "gpu_model_raw": "H100 SXM5 80GB",
  "gpu_key": "H100 80GB SXM",
  "gpu_family": "H100",
  "gpu_form": "SXM",
  "gpu_form_source": "provider",
  "gpu_partition": null,
  "gpu_recognised": true,
  "gpu_count": 1,
  "vram_gb": 80,
  "currency": "USD",
  "price_total_hr": 3.25,
  "price_total_hr_usd": 3.25,
  "price_per_gpu_hr": 3.25,
  "price_per_gpu_hr_usd": 3.25,
  "pricing_type": "on-demand",
  "vcpu": 30,
  "ram_gb": 120,
  "region": null,
  "available": null,
  "notes": "instance type 1H100.80S.30V",
  "listing_url": "https://cloud.datacrunch.io/signin"
}
```

Sort on `price_per_gpu_hr_usd`. `price_per_gpu_hr` is in the provider's own
currency, which is euros for Scaleway and dollars for everyone else. Fractional
GPU plans (Vultr sells eighths of an A16) have a null per GPU price on purpose,
because a per GPU rate you cannot actually buy is not a real number.

Files:

- `data/prices.json` current snapshot, every offer
- `data/status.json` per provider health for the latest run, including what each
  collector asked for and what it deliberately dropped
- `data/history/v2/YYYY-MM.jsonl` one line per run, cheapest price per provider
  per GPU key, append only
- `data/history/*.jsonl` the older schema 1 lines, frozen. See
  [`data/history/README.md`](data/history/README.md) before you read across the
  two

## The key tells you the form, because the form is the product

`gpu_key` is what you group and compare on. It is family, then VRAM, then the
form factor where the form factor matters:

```
H100 80GB SXM        H100 80GB PCIe        H100 94GB NVL
A100 80GB SXM        A100 80GB PCIe
RTX PRO 6000 Blackwell 96GB Server         RTX PRO 6000 Blackwell 96GB Max-Q
```

An H100 SXM and an H100 PCIe both carry 80 GB and are not the same product. The
SXM part is meaningfully faster and normally dearer. Keying both as `H100 80GB`,
which is what this feed did before, meant a naive cheapest match could hand you a
PCIe card when your job needed SXM. Now it cannot: they are different keys.

The same split applies to A100 40 and 80, H200, B200, B300, V100, P100, and the
RTX PRO 6000 Blackwell, which NVIDIA sells as a Server Edition, a Workstation
Edition and a Max-Q Workstation Edition at the same 96 GB and very different
sustained performance.

### What "(form unstated)" means

Some listings never say. RunPod sells a "B200", DataCrunch sells an
"RTX PRO 6000 96GB", and neither string nor either API says which build it is.
Those get their own key:

```
B200 180GB (form unstated)
RTX PRO 6000 Blackwell 96GB (form unstated)
```

We do not guess, and we do not quietly file them under a known form. So a search
for `H100 80GB SXM` will never return a card that might not be SXM. If you are
happy with either, ask for both keys on purpose.

Every offer also carries `gpu_form_source`, which is how we know:

- `provider` the provider's own listing says so, in its name or in a second name
  it publishes for the same part
- `single-form-part` the part is only manufactured in one form, so there is
  nothing to disambiguate. An L40S is a PCIe card and nothing else
- `unknown` nobody said, and the part exists in more than one form. `gpu_form` is
  null and the key says `(form unstated)`

`gpu_partition` is set when a listing is a slice of a card rather than a card,
for example RunPod's MIG partitions of an RTX PRO 6000. Those keys end in `MIG`.

## Read this before you trust a number

`METHODOLOGY.md` says exactly where each number comes from and what it excludes.
The short version: these are list prices for a single machine, they exclude
storage, egress and tax, spot and on-demand are tagged separately and should not
be compared, and a marketplace price is what one host was asking at one moment.

No referral links, no affiliate links, no sponsored placement. Ranking is price,
nothing else.

## Why is GPU X not here

Usually because of a coverage limit, not because nobody rents it. Each collector
publishes what it actually asks for, in `COVERAGE` at the top of its module, in
`data/status.json`, and in the table further down this page. The two worth
knowing without reading anything else:

- **Vast.ai** has no "give me everything" API call. Its search answers one GPU
  name at a time and caps a broad query at 64 rows. So we query a built in list
  of names and also sample the live marketplace from six angles each run and
  query anything new that turns up. Every name we asked for is in
  `status.json` under `vastai.meta.models_queried`. A model in neither the list
  nor the sample is genuinely missing, and that is the honest limit.
- **Akamai Cloud** publishes RTX PRO 6000 plans on its pricing page that its
  public plan API does not return, so those are missing here.

Whole providers are missing too, mostly because their price catalog needs an
account key. `METHODOLOGY.md` names them.

<!-- BEGIN GENERATED -->
Last checked **2026-08-18T08:03:50Z**. 510 live offers from 8 providers.

Euro prices converted at the ECB reference rate published 2026-08-17, 1 EUR = 1.1593 USD.

## Cheapest on-demand price per GPU

One row per provider, cheapest configuration first. On-demand only, no spot and no reserved pricing. Prices exclude storage, bandwidth and tax unless noted in `data/prices.json`.

### B200 180GB SXM

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $6.11 | DataCrunch | B200 SXM6 180GB | SXM | the provider says so | 1 | on-demand |
| $6.23 | DataCrunch | B200 CC SXM6 180GB | SXM | the provider says so | 2 | on-demand |
| $6.69 | Lambda | NVIDIA B200 SXM6 | SXM | the provider says so | 8 | on-demand |

### B200 180GB (form unstated)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $5.88 | Vast.ai | B200 | not stated | nobody says | 1 | on-demand |
| $5.98 | RunPod | NVIDIA B200 | not stated | nobody says | 1 | on-demand |

### H200 141GB SXM

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $3.59 | RunPod | NVIDIA H200 | SXM | the provider says so | 1 | on-demand |
| $4.00 | DataCrunch | H200 SXM5 141GB | SXM | the provider says so | 1 | on-demand |
| $4.47 | DigitalOcean | NVIDIA HGX H200 | SXM | the provider says so | 1 | on-demand |

### H200 141GB NVL

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $3.28 | Vast.ai | H200 NVL | NVL | the provider says so | 1 | on-demand |
| $3.79 | RunPod | NVIDIA H200 NVL | NVL | the provider says so | 1 | on-demand |

### H200 141GB (form unstated)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $3.94 | Vast.ai | H200 | not stated | nobody says | 1 | on-demand |

### H100 80GB SXM

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.74 | Vast.ai | H100 SXM | SXM | the provider says so | 1 | on-demand |
| $2.69 | RunPod | NVIDIA H100 80GB HBM3 | SXM | the provider says so | 1 | on-demand |
| $3.25 | DataCrunch | H100 SXM5 80GB | SXM | the provider says so | 1 | on-demand |
| $3.84 * | Scaleway | H100-SXM | SXM | the provider says so | 2 | on-demand |
| $3.99 | Lambda | NVIDIA H100 SXM | SXM | the provider says so | 8 | on-demand |
| $4.41 | DigitalOcean | NVIDIA HGX H100 | SXM | the provider says so | 1 | on-demand |

\* the provider quotes this one in euros, converted here at the ECB daily rate

### H100 80GB PCIe

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.87 | Vast.ai | H100 PCIE | PCIe | the provider says so | 1 | on-demand |
| $1.99 | RunPod | NVIDIA H100 PCIe | PCIe | the provider says so | 1 | on-demand |
| $3.29 | Lambda | NVIDIA H100 PCIe | PCIe | the provider says so | 1 | on-demand |
| $3.32 * | Scaleway | H100-PCIe | PCIe | the provider says so | 1 | on-demand |

\* the provider quotes this one in euros, converted here at the ECB daily rate

### H100 94GB NVL

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $2.58 | Vast.ai | H100 NVL | NVL | the provider says so | 1 | on-demand |
| $2.59 | RunPod | NVIDIA H100 NVL | NVL | the provider says so | 1 | on-demand |

### A100 80GB SXM

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.39 | RunPod | NVIDIA A100-SXM4-80GB | SXM | the provider says so | 1 | on-demand |
| $1.79 | DataCrunch | A100 SXM4 80GB | SXM | the provider says so | 1 | on-demand |
| $2.79 | Lambda | NVIDIA A100 SXM | SXM | the provider says so | 8 | on-demand |

### A100 80GB PCIe

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.19 | RunPod | NVIDIA A100 80GB PCIe | PCIe | the provider says so | 1 | on-demand |

### A100 40GB SXM

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.736 | Vast.ai | A100 SXM4 | SXM | the provider says so | 1 | on-demand |
| $1.00 | RunPod | NVIDIA A100-SXM4-40GB | SXM | the provider says so | 1 | on-demand |
| $1.29 | DataCrunch | A100 SXM4 40GB | SXM | the provider says so | 1 | on-demand |
| $1.99 | Lambda | NVIDIA A100 SXM | SXM | the provider says so | 1 | on-demand |

### A100 40GB PCIe

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.656 | Vast.ai | A100 PCIE | PCIe | the provider says so | 1 | on-demand |
| $1.99 | Lambda | NVIDIA A100 PCIe | PCIe | the provider says so | 1 | on-demand |

### RTX PRO 6000 Blackwell 96GB Server

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.01 | Vast.ai | RTX PRO 6000 S | Server | the provider says so | 1 | on-demand |
| $1.69 | RunPod | NVIDIA RTX PRO 6000 Blackwell Server Edition | Server | the provider says so | 1 | on-demand |

### RTX PRO 6000 Blackwell 96GB Workstation

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.801 | Vast.ai | RTX PRO 6000 WS | Workstation | the provider says so | 1 | on-demand |
| $1.69 | RunPod | NVIDIA RTX PRO 6000 Blackwell Workstation Edition | Workstation | the provider says so | 1 | on-demand |

### RTX PRO 6000 Blackwell 96GB Max-Q

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.64 | RunPod | NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition | Max-Q | the provider says so | 1 | on-demand |

### RTX PRO 6000 Blackwell 96GB (form unstated)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.89 | DataCrunch | RTX PRO 6000 96GB | not stated | nobody says | 1 | on-demand |
| $1.93 | DataCrunch | RTX PRO 6000 CC 96GB | not stated | nobody says | 1 | on-demand |

### L40S 48GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.737 | Vast.ai | L40S | PCIe | only made in one form | 1 | on-demand |
| $0.790 | RunPod | NVIDIA L40S | PCIe | only made in one form | 1 | on-demand |
| $1.37 | DataCrunch | L40S 48GB | PCIe | only made in one form | 1 | on-demand |
| $1.57 | DigitalOcean | NVIDIA L40S | PCIe | only made in one form | 1 | on-demand |
| $1.67 | Vultr | NVIDIA_L40S | PCIe | only made in one form | 1 | on-demand |
| $1.70 * | Scaleway | L40S | PCIe | only made in one form | 1 | on-demand |

\* the provider quotes this one in euros, converted here at the ECB daily rate

### RTX 6000 Ada 48GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.541 | Vast.ai | RTX 6000Ada | PCIe | only made in one form | 1 | on-demand |
| $0.740 | RunPod | NVIDIA RTX 6000 Ada Generation | PCIe | only made in one form | 1 | on-demand |
| $1.04 | DataCrunch | RTX 6000 Ada 48GB | PCIe | only made in one form | 1 | on-demand |
| $1.57 | DigitalOcean | NVIDIA RTX 6000 Ada Generation | PCIe | only made in one form | 1 | on-demand |

### RTX A6000 48GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.330 | RunPod | NVIDIA RTX A6000 | PCIe | only made in one form | 1 | on-demand |
| $0.404 | Vast.ai | RTX A6000 | PCIe | only made in one form | 1 | on-demand |
| $0.610 | DataCrunch | RTX A6000 48GB | PCIe | only made in one form | 1 | on-demand |
| $1.09 | Lambda | NVIDIA A6000 | PCIe | only made in one form | 1 | on-demand |

### A40 48GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.440 | RunPod | NVIDIA A40 | PCIe | only made in one form | 1 | on-demand |

### RTX 5090 32GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.303 | Vast.ai | RTX 5090 | not stated | nobody says | 1 | on-demand |
| $0.690 | RunPod | NVIDIA GeForce RTX 5090 | not stated | nobody says | 1 | on-demand |

### RTX 4090 24GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.283 | Vast.ai | RTX 4090 | not stated | nobody says | 1 | on-demand |
| $0.340 | RunPod | NVIDIA GeForce RTX 4090 | not stated | nobody says | 1 | on-demand |

### RTX 3090 24GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.103 | Vast.ai | RTX 3090 | not stated | nobody says | 1 | on-demand |
| $0.220 | RunPod | NVIDIA GeForce RTX 3090 | not stated | nobody says | 1 | on-demand |

### L4 24GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.202 | Vast.ai | L4 | PCIe | only made in one form | 1 | on-demand |
| $0.490 | RunPod | NVIDIA L4 | PCIe | only made in one form | 1 | on-demand |
| $0.913 * | Scaleway | L4 | PCIe | only made in one form | 1 | on-demand |

\* the provider quotes this one in euros, converted here at the ECB daily rate

### A10 24GB

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.243 | Vast.ai | A10 | PCIe | only made in one form | 1 | on-demand |
| $1.29 | Lambda | NVIDIA A10 | PCIe | only made in one form | 1 | on-demand |

### V100 16GB SXM

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.230 | RunPod | Tesla V100-SXM2-16GB | SXM | the provider says so | 1 | on-demand |

### V100 16GB PCIe

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.190 | RunPod | Tesla V100-PCIE-16GB | PCIe | the provider says so | 1 | on-demand |

### V100 16GB (form unstated)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.170 | DataCrunch | Tesla V100 16GB | not stated | nobody says | 1 | on-demand |
| $0.790 | Lambda | NVIDIA Tesla V100 | not stated | nobody says | 8 | on-demand |

## Cheapest spot and interruptible price per GPU

These can be reclaimed while your job is running. Do not compare them against the on-demand numbers above as if they were the same product.

### B200 180GB SXM (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $3.06 | DataCrunch | B200 SXM6 180GB | SXM | the provider says so | 1 | spot |
| $3.12 | DataCrunch | B200 CC SXM6 180GB | SXM | the provider says so | 4 | spot |

### B200 180GB (form unstated) (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $5.98 | RunPod | NVIDIA B200 | not stated | nobody says | 1 | spot |

### H200 141GB SXM (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $2.00 | DataCrunch | H200 SXM5 141GB | SXM | the provider says so | 1 | spot |
| $3.59 | RunPod | NVIDIA H200 | SXM | the provider says so | 1 | spot |

### H200 141GB NVL (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $3.79 | RunPod | NVIDIA H200 NVL | NVL | the provider says so | 1 | spot |

### H100 80GB SXM (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.62 | DataCrunch | H100 SXM5 80GB | SXM | the provider says so | 1 | spot |
| $2.69 | RunPod | NVIDIA H100 80GB HBM3 | SXM | the provider says so | 1 | spot |

### H100 80GB PCIe (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.99 | RunPod | NVIDIA H100 PCIe | PCIe | the provider says so | 1 | spot |

### H100 94GB NVL (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $2.59 | RunPod | NVIDIA H100 NVL | NVL | the provider says so | 1 | spot |

### A100 80GB SXM (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.895 | DataCrunch | A100 SXM4 80GB | SXM | the provider says so | 1 | spot |
| $1.39 | RunPod | NVIDIA A100-SXM4-80GB | SXM | the provider says so | 1 | spot |

### A100 80GB PCIe (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.19 | RunPod | NVIDIA A100 80GB PCIe | PCIe | the provider says so | 1 | spot |

### A100 40GB SXM (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.645 | DataCrunch | A100 SXM4 40GB | SXM | the provider says so | 1 | spot |
| $1.00 | RunPod | NVIDIA A100-SXM4-40GB | SXM | the provider says so | 1 | spot |

### RTX PRO 6000 Blackwell 96GB Server (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.69 | RunPod | NVIDIA RTX PRO 6000 Blackwell Server Edition | Server | the provider says so | 1 | spot |

### RTX PRO 6000 Blackwell 96GB Workstation (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.69 | RunPod | NVIDIA RTX PRO 6000 Blackwell Workstation Edition | Workstation | the provider says so | 1 | spot |

### RTX PRO 6000 Blackwell 96GB Max-Q (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $1.64 | RunPod | NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition | Max-Q | the provider says so | 1 | spot |

### RTX PRO 6000 Blackwell 96GB (form unstated) (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.945 | DataCrunch | RTX PRO 6000 96GB | not stated | nobody says | 1 | spot |
| $0.964 | DataCrunch | RTX PRO 6000 CC 96GB | not stated | nobody says | 1 | spot |

### L40S 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.685 | DataCrunch | L40S 48GB | PCIe | only made in one form | 1 | spot |
| $0.790 | RunPod | NVIDIA L40S | PCIe | only made in one form | 1 | spot |

### RTX 6000 Ada 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.520 | DataCrunch | RTX 6000 Ada 48GB | PCIe | only made in one form | 1 | spot |
| $0.740 | RunPod | NVIDIA RTX 6000 Ada Generation | PCIe | only made in one form | 1 | spot |

### RTX A6000 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.305 | DataCrunch | RTX A6000 48GB | PCIe | only made in one form | 1 | spot |
| $0.330 | RunPod | NVIDIA RTX A6000 | PCIe | only made in one form | 1 | spot |

### A40 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.440 | RunPod | NVIDIA A40 | PCIe | only made in one form | 1 | spot |

### RTX 5090 32GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.690 | RunPod | NVIDIA GeForce RTX 5090 | not stated | nobody says | 1 | spot |

### RTX 4090 24GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.340 | RunPod | NVIDIA GeForce RTX 4090 | not stated | nobody says | 1 | spot |

### RTX 3090 24GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.220 | RunPod | NVIDIA GeForce RTX 3090 | not stated | nobody says | 1 | spot |

### L4 24GB (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.490 | RunPod | NVIDIA L4 | PCIe | only made in one form | 1 | spot |

### V100 16GB SXM (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.230 | RunPod | Tesla V100-SXM2-16GB | SXM | the provider says so | 1 | spot |

### V100 16GB PCIe (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.190 | RunPod | Tesla V100-PCIE-16GB | PCIe | the provider says so | 1 | spot |

### V100 16GB (form unstated) (spot)

| $/GPU/hr | Provider | Listed as | Form | How we know the form | GPUs in config | Type |
|---|---|---|---|---|---|---|
| $0.0850 | DataCrunch | Tesla V100 16GB | not stated | nobody says | 1 | spot |

## Sources in this run

| Provider | Offers | Models | Status | Where the numbers come from |
|---|---|---|---|---|
| [Akamai Cloud (Linode)](https://www.linode.com) | 13 | 2 | ok | https://api.linode.com/v4/linode/types |
| [DataCrunch](https://datacrunch.io) | 110 | 12 | ok | https://api.datacrunch.io/v1/instance-types |
| [DigitalOcean](https://www.digitalocean.com) | 13 | 7 | ok | https://www.digitalocean.com/pricing/gpu-droplets |
| [Lambda](https://lambda.ai) | 22 | 11 | ok | https://lambda.ai/service/gpu-cloud |
| [RunPod](https://www.runpod.io) | 138 | 46 | ok | https://api.runpod.io/graphql |
| [Scaleway](https://www.scaleway.com) | 20 | 5 | ok | https://api.scaleway.com/instance/v1/zones/{zone}/products/servers |
| [Vast.ai](https://vast.ai) | 179 | 73 | ok | https://console.vast.ai/api/v0/search/asks/ |
| [Vultr](https://www.vultr.com) | 15 | 2 | ok | https://api.vultr.com/v2/plans?type=vcg&per_page=500 |

## What each source does and does not cover

A missing GPU is usually a coverage limit, not a price of zero. This is what each collector actually asks for.

| Provider | Covered |
|---|---|
| Akamai Cloud (Linode) | plans in the public /linode/types catalog that report gpus > 0. Akamai's own pricing page lists RTX PRO 6000 plans that this API does not return, so those are missing here |
| DataCrunch | every instance type in the public catalog that has a GPU, on-demand and spot |
| DigitalOcean | every card on the public GPU Droplet pricing page, including the 12 month reserved cards, which are tagged and kept out of the on-demand tables |
| Lambda | every row of the public pricing page, all four GPU count tabs. Lambda's instance API needs a key so on-demand availability is not covered |
| RunPod | every GPU type in RunPod's public catalog, on-demand and spot, but only for the markets RunPod flags as actually offering that card |
| Scaleway | GPU instance types in nine European zones. Scaleway sells other GPU products (Dedibox, managed inference) that this endpoint does not list |
| Vast.ai | a fixed base list of GPU names plus whatever a six angle sample of the marketplace turns up; verified hosts only; single GPU offers preferred. A model outside both the base list and the sample does not appear |
| Vultr | cloud GPU (vcg) plans only, fractional and whole. Vultr bare metal GPU plans live on another endpoint and are not covered |

Vast.ai is the one that needs a number on it. This run asked for 70 GPU names, 43 of which came from sampling the live marketplace rather than from the built in list, and 1 of them had no verified stock. Anything Vast rents under a name outside that set is not in this table.

Full data for all 96 GPU models we saw this run is in [`data/prices.json`](data/prices.json).
<!-- END GENERATED -->

## Run it yourself

Python 3 and nothing else. No packages to install, the whole thing is standard
library. Tested on 3.12 (what the Action runs) and 3.14.

```bash
python3 collect.py && python3 render_readme.py
```

Exit code 0 means every provider collected cleanly. 2 means at least one
provider failed or tripped a sanity check. 3 means all of them failed, and in
that case the snapshot is left untouched.

## Corrections

If a price here does not match what the provider is showing you, open an issue
with the provider, the GPU, and a link. Wrong data is the only bug that matters
in this repo.

MIT licensed.
