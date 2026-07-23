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
  | jq -r '.offers[] | select(.gpu_key=="H100 80GB" and .pricing_type=="on-demand")
           | [.price_per_gpu_hr_usd, .provider, .gpu_model_raw, .gpu_form] | @tsv' \
  | sort -n | head
```

One offer, exactly as it appears in the file:

```json
{
  "provider": "datacrunch",
  "gpu_model_raw": "H100 SXM5 80GB",
  "gpu_key": "H100 80GB",
  "gpu_family": "H100",
  "gpu_form": "SXM",
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
- `data/status.json` per provider health for the latest run
- `data/history/YYYY-MM.jsonl` one line per run, cheapest price per provider per
  GPU model, append only

## Read this before you trust a number

`METHODOLOGY.md` says exactly where each number comes from and what it excludes.
The short version: these are list prices for a single machine, they exclude
storage, egress and tax, spot and on-demand are tagged separately and should not
be compared, and a marketplace price is what one host was asking at one moment.

No referral links, no affiliate links, no sponsored placement. Ranking is price,
nothing else.

<!-- BEGIN GENERATED -->
Last checked **2026-07-23T21:32:10Z**. 401 live offers from 8 providers.

Euro prices converted at the ECB reference rate published 2026-07-23, 1 EUR = 1.1392 USD.

## Cheapest on-demand price per GPU

One row per provider, cheapest configuration first. On-demand only, no spot and no reserved pricing. Prices exclude storage, bandwidth and tax unless noted in `data/prices.json`.

### B200 180GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $5.89 | RunPod | NVIDIA B200 | not stated | 1 | on-demand |
| $6.11 | DataCrunch | B200 SXM6 180GB | SXM | 1 | on-demand |
| $6.50 | Vast.ai | B200 | not stated | 1 | on-demand |
| $6.69 | Lambda | NVIDIA B200 SXM6 | SXM | 8 | on-demand |

### H200 141GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $3.40 | Vast.ai | H200 NVL | NVL | 1 | on-demand |
| $3.44 | DigitalOcean | NVIDIA HGX H200 | SXM | 1 | on-demand |
| $3.59 | RunPod | NVIDIA H200 | not stated | 1 | on-demand |
| $3.94 | Vast.ai | H200 | not stated | 1 | on-demand |
| $4.00 | DataCrunch | H200 SXM5 141GB | SXM | 1 | on-demand |

### H100 80GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $1.74 | Vast.ai | H100 SXM | SXM | 1 | on-demand |
| $1.99 | RunPod | NVIDIA H100 PCIe | PCIe | 1 | on-demand |
| $2.69 | RunPod | NVIDIA H100 80GB HBM3 | not stated | 1 | on-demand |
| $3.25 | DataCrunch | H100 SXM5 80GB | SXM | 1 | on-demand |
| $3.27 * | Scaleway | H100-PCIe | PCIe | 1 | on-demand |
| $3.29 | Lambda | NVIDIA H100 PCIe | PCIe | 1 | on-demand |

\* the provider quotes this one in euros, converted here at the ECB daily rate

### A100 80GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.563 | Vast.ai | A100 PCIE | PCIe | 1 | on-demand |
| $1.19 | RunPod | NVIDIA A100 80GB PCIe | PCIe | 1 | on-demand |
| $1.39 | RunPod | NVIDIA A100-SXM4-80GB | SXM | 1 | on-demand |
| $1.79 | DataCrunch | A100 SXM4 80GB | SXM | 1 | on-demand |
| $2.79 | Lambda | NVIDIA A100 SXM | SXM | 8 | on-demand |

### A100 40GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.469 | Vast.ai | A100 PCIE | PCIe | 1 | on-demand |
| $0.602 | Vast.ai | A100 SXM4 | SXM | 1 | on-demand |
| $1.00 | RunPod | NVIDIA A100-SXM4-40GB | SXM | 1 | on-demand |
| $1.29 | DataCrunch | A100 SXM4 40GB | SXM | 1 | on-demand |
| $1.99 | Lambda | NVIDIA A100 SXM | SXM | 1 | on-demand |
| $1.99 | Lambda | NVIDIA A100 PCIe | PCIe | 1 | on-demand |

### RTX PRO 6000 Blackwell 96GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.500 | RunPod | NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition | not stated | 1 | on-demand |
| $1.69 | RunPod | NVIDIA RTX PRO 6000 Blackwell Server Edition | not stated | 1 | on-demand |
| $1.69 | RunPod | NVIDIA RTX PRO 6000 Blackwell Workstation Edition | not stated | 1 | on-demand |
| $1.89 | DataCrunch | RTX PRO 6000 96GB | not stated | 1 | on-demand |
| $1.93 | DataCrunch | RTX PRO 6000 CC 96GB | not stated | 1 | on-demand |

### L40S 48GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.790 | RunPod | NVIDIA L40S | PCIe | 1 | on-demand |
| $1.37 | DataCrunch | L40S 48GB | PCIe | 1 | on-demand |
| $1.57 | DigitalOcean | NVIDIA L40S | PCIe | 1 | on-demand |
| $1.67 | Vultr | NVIDIA_L40S | PCIe | 1 | on-demand |
| $1.67 * | Scaleway | L40S | PCIe | 1 | on-demand |

\* the provider quotes this one in euros, converted here at the ECB daily rate

### RTX 6000 Ada 48GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.297 | Vast.ai | RTX 6000Ada | not stated | 1 | on-demand |
| $0.740 | RunPod | NVIDIA RTX 6000 Ada Generation | not stated | 1 | on-demand |
| $1.04 | DataCrunch | RTX 6000 Ada 48GB | not stated | 1 | on-demand |
| $1.57 | DigitalOcean | NVIDIA RTX 6000 Ada Generation | not stated | 1 | on-demand |

### RTX A6000 48GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.330 | RunPod | NVIDIA RTX A6000 | not stated | 1 | on-demand |
| $0.429 | Vast.ai | RTX A6000 | not stated | 1 | on-demand |
| $0.610 | DataCrunch | RTX A6000 48GB | not stated | 1 | on-demand |
| $1.09 | Lambda | NVIDIA A6000 | not stated | 1 | on-demand |

### A40 48GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.350 | RunPod | NVIDIA A40 | PCIe | 1 | on-demand |
| $1.71 | Vultr | NVIDIA_A40 | PCIe | 1 | on-demand |

### RTX 5090 32GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.303 | Vast.ai | RTX 5090 | not stated | 1 | on-demand |
| $0.690 | RunPod | NVIDIA GeForce RTX 5090 | not stated | 1 | on-demand |

### RTX 4090 24GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.276 | Vast.ai | RTX 4090 | not stated | 1 | on-demand |
| $0.340 | RunPod | NVIDIA GeForce RTX 4090 | not stated | 1 | on-demand |

### RTX 3090 24GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.103 | Vast.ai | RTX 3090 | not stated | 1 | on-demand |
| $0.220 | RunPod | NVIDIA GeForce RTX 3090 | not stated | 1 | on-demand |

### L4 24GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.390 | RunPod | NVIDIA L4 | PCIe | 1 | on-demand |
| $0.897 * | Scaleway | L4 | PCIe | 1 | on-demand |

\* the provider quotes this one in euros, converted here at the ECB daily rate

### A10 24GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $1.29 | Lambda | NVIDIA A10 | PCIe | 1 | on-demand |

### V100 16GB

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.136 | Vast.ai | Tesla V100 | not stated | 1 | on-demand |
| $0.170 | DataCrunch | Tesla V100 16GB | not stated | 1 | on-demand |
| $0.190 | RunPod | Tesla V100-PCIE-16GB | PCIe | 1 | on-demand |
| $0.230 | RunPod | Tesla V100-SXM2-16GB | not stated | 1 | on-demand |
| $0.790 | Lambda | NVIDIA Tesla V100 | not stated | 8 | on-demand |

## Cheapest spot and interruptible price per GPU

These can be reclaimed while your job is running. Do not compare them against the on-demand numbers above as if they were the same product.

### B200 180GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $2.14 | DataCrunch | B200 SXM6 180GB | SXM | 2 | spot |
| $5.49 | RunPod | NVIDIA B200 | not stated | 1 | spot |

### H200 141GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $1.40 | DataCrunch | H200 SXM5 141GB | SXM | 1 | spot |
| $3.99 | RunPod | NVIDIA H200 | not stated | 1 | spot |

### H100 80GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $1.14 | DataCrunch | H100 SXM5 80GB | SXM | 2 | spot |
| $1.99 | RunPod | NVIDIA H100 PCIe | PCIe | 1 | spot |
| $2.69 | RunPod | NVIDIA H100 80GB HBM3 | not stated | 1 | spot |

### A100 80GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.626 | DataCrunch | A100 SXM4 80GB | SXM | 1 | spot |
| $1.19 | RunPod | NVIDIA A100 80GB PCIe | PCIe | 1 | spot |
| $1.39 | RunPod | NVIDIA A100-SXM4-80GB | SXM | 1 | spot |

### A100 40GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.452 | DataCrunch | A100 SXM4 40GB | SXM | 1 | spot |

### RTX PRO 6000 Blackwell 96GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.661 | DataCrunch | RTX PRO 6000 96GB | not stated | 1 | spot |
| $0.675 | DataCrunch | RTX PRO 6000 CC 96GB | not stated | 1 | spot |
| $1.89 | RunPod | NVIDIA RTX PRO 6000 Blackwell Server Edition | not stated | 1 | spot |
| $1.89 | RunPod | NVIDIA RTX PRO 6000 Blackwell Workstation Edition | not stated | 1 | spot |

### L40S 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.479 | DataCrunch | L40S 48GB | PCIe | 1 | spot |
| $0.790 | RunPod | NVIDIA L40S | PCIe | 1 | spot |

### RTX 6000 Ada 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.364 | DataCrunch | RTX 6000 Ada 48GB | not stated | 1 | spot |
| $0.740 | RunPod | NVIDIA RTX 6000 Ada Generation | not stated | 1 | spot |

### RTX A6000 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.213 | DataCrunch | RTX A6000 48GB | not stated | 1 | spot |
| $0.330 | RunPod | NVIDIA RTX A6000 | not stated | 1 | spot |

### A40 48GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.300 | RunPod | NVIDIA A40 | PCIe | 1 | spot |

### RTX 5090 32GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.990 | RunPod | NVIDIA GeForce RTX 5090 | not stated | 1 | spot |

### RTX 4090 24GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.340 | RunPod | NVIDIA GeForce RTX 4090 | not stated | 1 | spot |

### RTX 3090 24GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.220 | RunPod | NVIDIA GeForce RTX 3090 | not stated | 1 | spot |

### L4 24GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.390 | RunPod | NVIDIA L4 | PCIe | 1 | spot |

### V100 16GB (spot)

| $/GPU/hr | Provider | Listed as | Form | GPUs in config | Type |
|---|---|---|---|---|---|
| $0.0595 | DataCrunch | Tesla V100 16GB | not stated | 1 | spot |
| $0.190 | RunPod | Tesla V100-PCIE-16GB | PCIe | 1 | spot |
| $0.230 | RunPod | Tesla V100-SXM2-16GB | not stated | 1 | spot |

## Sources in this run

| Provider | Offers | Models | Status | Where the numbers come from |
|---|---|---|---|---|
| [Akamai Cloud (Linode)](https://www.linode.com) | 13 | 2 | ok | https://api.linode.com/v4/linode/types |
| [DataCrunch](https://datacrunch.io) | 94 | 12 | ok | https://api.datacrunch.io/v1/instance-types |
| [DigitalOcean](https://www.digitalocean.com) | 12 | 6 | ok | https://www.digitalocean.com/pricing/gpu-droplets |
| [Lambda](https://lambda.ai) | 22 | 9 | ok | https://lambda.ai/service/gpu-cloud |
| [RunPod](https://www.runpod.io) | 152 | 42 | ok | https://api.runpod.io/graphql |
| [Scaleway](https://www.scaleway.com) | 20 | 4 | ok | https://api.scaleway.com/instance/v1/zones/{zone}/products/servers |
| [Vast.ai](https://vast.ai) | 69 | 26 | ok | https://console.vast.ai/api/v0/search/asks/ |
| [Vultr](https://www.vultr.com) | 19 | 3 | ok | https://api.vultr.com/v2/plans?type=vcg&per_page=500 |

Full data for all 60 GPU models we saw this run is in [`data/prices.json`](data/prices.json).
<!-- END GENERATED -->

## Run it yourself

Python 3.9 or newer, no dependencies to install.

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
