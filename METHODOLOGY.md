# Methodology

Where every number in this repo comes from, what it includes, and what it does
not. If something here is wrong, that is a bug worth an issue.

## Refresh

A GitHub Action runs `collect.py` once a day at 06:15 UTC and commits whatever
changed. You can also trigger it by hand from the Actions tab. Each run writes
three things:

- `data/prices.json` is replaced with the new snapshot
- `data/status.json` is replaced with the health of that run
- `data/history/v2/YYYY-MM.jsonl` gets one appended line holding the cheapest
  on-demand price per provider per GPU key

The history file is append only. Nothing in it is ever rewritten. That is the
audit trail: if the tables ever stop matching the prices, the history shows it.

### Schema versions

The snapshot carries `schema_version` and so does every history line.

Schema 2 (current, from 2026-07-23) put the form factor into `gpu_key`. Schema 1
keyed on family plus VRAM only, so `H100 80GB` covered both the SXM part and the
PCIe part.

The schema 1 history was not migrated and will not be. A schema 1 line records
one cheapest price for `H100 80GB` drawn from a mix of SXM and PCIe listings, and
there is no way to recover afterwards which form that number belonged to. Any
migration would have to invent it. Rewriting an append only store with an invented
value is worse than a labelled boundary, so the schema 1 lines stay byte for byte
where they were written, directly under `data/history/`, and schema 2 lines go in
`data/history/v2/`. Read them as two series that meet at the boundary, not as one.
`data/history/README.md` says the same thing next to the files.

## What each price means

All figures are US dollars per GPU per hour unless the row says otherwise.

Where a provider quotes a whole machine, we divide by the GPU count in that
machine. Where a provider already quotes per GPU (Lambda, DigitalOcean) we use
their number directly.

None of these prices include:

- persistent storage volumes
- network egress
- static IP addresses
- sales tax or VAT
- support plans

Two prices for the same chip are not always the same product. An H100 SXM and an
H100 PCIe both carry 80 GB, but the SXM part is meaningfully faster and normally
dearer. They are separate keys, `H100 80GB SXM` and `H100 80GB PCIe`, so nothing
that matches on the key can substitute one for the other. The next section says
how the key is built.

## Sources, one by one

### Vast.ai

`GET https://console.vast.ai/api/v0/search/asks/` with a JSON query. No key
needed. This is the same search the Vast console uses.

`dph_total` is the number we take. The API's own breakdown confirms it is
`gpuCostPerHour + diskHour`, where the disk part is a small default allocation.
Host bandwidth charges are not in it.

Two deliberate choices:

- We only keep machines Vast marks `verified`. The very cheapest listings on Vast
  are usually unverified or deverified hosts. Calling one of those "the cheapest
  H100" would be true and useless. If you want those, the filter is one flag in
  `providers/vastai.py`.
- We ask for single GPU offers first, and fall back to multi GPU only when there
  is no single GPU stock. So Vast rows are the price of renting one GPU. A larger
  Vast machine can be cheaper per GPU and we are not currently ranking those.

Vast is a marketplace, so a Vast price is one host's asking price at one moment.
It can change between our snapshot and your click. That is not a bug in the feed,
it is what a marketplace is.

**Coverage, which is the most likely reason a GPU you expected is missing.**
Vast's search API answers a query about one `gpu_name` at a time, and a broad
query comes back capped at 64 rows, so there is no call that returns the whole
marketplace. Each run therefore does two things:

1. queries a fixed base list of names, kept explicit at the top of
   `providers/vastai.py` so a rename upstream shows up as a missing model rather
   than as silence, and
2. samples the live marketplace from six angles (cheapest, dearest, most GPUs,
   most VRAM, least VRAM, most reliable) and queries any name that turns up and
   is not already in the base list.

Every name we ended up asking for is written to
`status.json` at `providers.vastai.meta.models_queried`, the ones the sample
added are in `models_discovered`, and the ones with no verified stock this run
are in `models_with_no_stock`. A GPU that Vast rents under a name in neither the
base list nor the sample window will not appear here. That is the honest limit of
this collector and it is why the sample exists.

### RunPod

`POST https://api.runpod.io/graphql`, the public `gpuTypes` query. No key needed.

RunPod publishes four numbers per GPU: secure cloud and community cloud, each
with an on-demand and a spot rate. We emit all four as separate rows tagged in
`pricing_type` and described in `notes`. Community cloud is third party hardware
and is normally the cheaper of the two. Storage and egress are separate.

The same response also carries `secureCloud` and `communityCloud` booleans, and
we only publish a price for a market that is flagged true. RunPod keeps stale
numbers on file for markets that are closed. The H200 NVL came back at a
community price of $0.50 against $3.79 secure, with `communityCloud` false and no
community H200 NVL anywhere on RunPod's own pricing page. That $0.50 would have
sat at the top of the H200 NVL table as the cheapest option and nobody could have
bought it. Every price dropped this way is listed in `status.json` at
`providers.runpod.meta.prices_dropped_market_not_offered`, so the filter is
auditable rather than silent.

### DataCrunch

`GET https://api.datacrunch.io/v1/instance-types`. No key needed. The response
carries `price_per_hour` and `spot_price` per instance type, and it labels its
own currency as USD. We divide by the GPU count. Storage is separate.

### Lambda

Parsed from the public pricing table at <https://lambda.ai/service/gpu-cloud>.
Lambda's instance API needs an account key, so we read the page. The table is
properly marked up, with a `data-plan` attribute per row and a labelled
`PRICE/GPU/HR` cell, and it already quotes per GPU per hour. There are four tabs
(8x, 4x, 2x, 1x) and we read all four, recording the GPU count on each row. The
page footnote says prices exclude sales tax, so ours do too.

If Lambda changes that table's markup, the parser raises and Lambda drops out of
the run rather than reporting a stale price.

### DigitalOcean

Parsed from <https://www.digitalocean.com/pricing/gpu-droplets>. Two sets of
cards, both quoting per GPU per hour:

- the self serve On-Demand cards, tagged `on-demand`
- the 12 Month Reserved cards, tagged `reserved-12mo`

The reserved cards say "Contact sales", so they are not a price you can click and
get. They are in the data but excluded from the on-demand tables. Note that
DigitalOcean's page currently carries a notice about new on-demand pricing taking
effect on a future date. We capture that notice in `data/status.json`.

### Scaleway

`GET https://api.scaleway.com/instance/v1/zones/<zone>/products/servers` for
every zone, no key needed. We keep the zone on each row because availability and
lineup differ by zone.

**This API returns euros and does not say so.** Scaleway's public pricing page
column header reads "Price (EUR/hour)" and the numbers line up exactly (the API
returns 0.7875 for `L4-1-24G`, the page shows EUR 0.79). Every Scaleway row is
tagged `"currency": "EUR"`, keeps its euro price in `price_per_gpu_hr`, and gets
a converted `price_per_gpu_hr_usd` using the European Central Bank daily
reference rate. The exact rate and its publication date are recorded in the `fx`
block of every snapshot. If the ECB feed is unreachable, the dollar fields are
null and Scaleway is left out of the dollar tables for that run. We never
convert with a guessed rate.

One more Scaleway quirk we handle: its `gpu_memory` field is per GPU, not the
instance total. `L4-8-24G` reports 24 GiB and an L4 has 24 GB. Dividing that by
eight would have produced a fictional 3 GB L4.

### Akamai Cloud (Linode)

`GET https://api.linode.com/v4/linode/types`, no key needed. We keep plans with
`gpus` greater than zero. The GPU model only appears in the plan label, so we
read it out of the label and keep the full label in `notes`.

Known gap: Akamai's own pricing page lists RTX PRO 6000 Blackwell plans that this
public API does not return. We list what the API returns and we are not going to
invent the rest. If you need those, check Akamai's pricing page directly.

We skip the NETINT Quadra plans. Those are video transcoding accelerators, not
GPUs, and they do not belong in a GPU price table.

### Vultr

`GET https://api.vultr.com/v2/plans?type=vcg`, no key needed. This is the
provisioning catalog, so `hourly_cost` is the rate you are billed.

Vultr sells fractional GPUs. A plan can be one eighth of an A16. A per GPU rate
derived from a fraction would be a number you cannot buy, so fractional plans
carry `price_per_gpu_hr: null` and only their whole instance price. They stay in
the JSON, they just do not appear in the per GPU rankings.

Vultr's marketing pages block automated requests, so the cross check here is
internal: hourly times the monthly cap equals the published monthly figure (672
hours on the L40S plans, about 730 on the rest).

Vultr bare metal GPU plans use a different endpoint and are not covered.

## Currency

Everything is USD except Scaleway, which is EUR converted at the ECB daily
reference rate. See the `currency`, `price_per_gpu_hr` and `price_per_gpu_hr_usd`
fields on each offer, and the `fx` block on the snapshot.

## GPU name normalization

Every provider spells the same chip differently. `NVIDIA A100-SXM4-80GB`,
`A100 SXM4 80GB` and `A100 SXM` are all the same part. We map raw names onto a
`gpu_key` of family, then VRAM, then form factor where the form factor matters:
`H100 80GB SXM`, `A100 40GB PCIe`, `RTX PRO 6000 Blackwell 96GB Max-Q`.

Rules we hold to:

- We never merge different VRAM sizes. An A100 40GB and an A100 80GB are separate
  keys.
- For families that ship in more than one form which are not substitutable, the
  form is part of the key. Today that list is H100, H200, H800, A100, A800, B200,
  B300, GB200, GB300, V100, P100 and the RTX PRO 6000 Blackwell. It is a named
  list in `lib/normalize.py`, not something derived from whatever happens to be
  in stock, so a key does not change shape when a provider adds or drops a card.
- We never guess a form. It comes from what the provider itself publishes, or
  from the part only existing in one form. When neither applies the key ends in
  `(form unstated)` and stays separate from every known form, so an unstated part
  can never be handed to someone who asked for a specific one.
- A chip we do not recognise keeps its raw name as its key and is flagged with
  `gpu_recognised: false`. It stays in the JSON and stays out of the headline
  tables. We would rather show you nothing than file a part under the wrong name.

`gpu_form_source` on every offer says which of those three applies: `provider`,
`single-form-part`, or `unknown`.

Two cases worth spelling out because they look like guesses and are not:

- RunPod publishes two names per GPU type. The id is the nvidia-smi product
  string and the displayName is the console label, and they carry different
  information. The id `NVIDIA H100 80GB HBM3` does not say SXM. The displayName
  for that same type is `H100 SXM`. We read both, so that row is SXM on RunPod's
  own authority.
- Vast.ai lists `RTX PRO 6000 S` and `RTX PRO 6000 WS`. Vast's own pricing pages
  spell those out, at `vast.ai/pricing/gpu/RTX-PRO-6000-S` ("RTX PRO 6000
  Blackwell Server Edition") and `vast.ai/pricing/gpu/RTX-PRO-6000-WS` ("RTX PRO
  6000 Blackwell Workstation Edition"). So the shorthand is Vast stating the
  variant, not us inferring it.

### VRAM

Cards do not report round numbers. An L40S with ECC on reports 46068 MiB and is
sold as a 48 GB card, because ECC on a GDDR6 board costs 6.25 percent. A
DataCrunch B300 is labelled 268GB and Vast reports 275040 MiB for the same chip,
which NVIDIA sells as 288 GB. So we snap a reported figure onto the capacity the
part is sold as, up to 8 percent up and 2 percent down, and otherwise leave the
number exactly as reported rather than force it into a bucket. The direction is
not symmetric on purpose: what a card reports as usable sits at or below what it
is sold as.

Before this rule the feed split one product into two keys, listing Vast's L40S as
`L40S 45GB` while everyone else's was `L40S 48GB`. A false split is the same bug
as a false merge, pointing the other way.

The rules are in `lib/normalize.py` and are meant to be read.

## When something breaks

Scrapers rot. This one is built to fail loudly instead of quietly:

- Every collector asserts a minimum number of rows and raises if the source
  returns fewer. A layout change usually collapses the row count to zero.
- Every price is checked against a plausible band. A parser that grabs a monthly
  figure or a GB count instead of a price lands outside it.
- Every run compares the cheapest price per model against the previous run.
  A move over 2x on a fixed price list, or over 5x on a marketplace, is flagged
  in `data/status.json`, printed in the README, and turns the job red.

A provider that fails is dropped from that run's snapshot entirely. It is never
backfilled with an older number. The README says which providers were dropped and
why. `collect.py` exits 2 when anything failed or was flagged, and exits 3 and
refuses to write the snapshot if every provider failed.

## What this does not cover

- Every GPU each provider rents. Each collector has a coverage limit, it is
  stated in `COVERAGE` at the top of the module, it is copied into
  `data/status.json` and into the README table, and the two that bite hardest are
  Vast's per name search and Akamai's plan API, which omits the RTX PRO 6000
  plans Akamai's own pricing page lists.
- Reserved and committed use pricing, other than DigitalOcean's 12 month cards
  which are tagged and excluded from the on-demand tables
- Serverless and per token inference pricing
- Kubernetes, managed training platforms, and anything that is not a rentable GPU
  by the hour
- Storage, egress, IP and support costs
- Region by region price differences, except on Scaleway and Vultr where the
  source gives them to us
- Live capacity. `available` is populated only where a provider tells us
  (RunPod stock status, Vast rentable). Elsewhere it is null. A listed price is
  not a promise there is a free machine.
- The big three hyperscalers. AWS, GCP and Azure are not here yet.
- Providers whose prices we could not get cleanly. Novita, Hyperstack, Prime
  Intellect and CUDO all require an account key for their price catalogs, and
  TensorDock's marketplace API is gone. We would rather leave them out than
  transcribe a marketing page by hand and let it rot.
- Aggregators and resellers. Their price is their own price, not the underlying
  cloud's, and listing it under the cloud's name would be misleading.

## Money

There are no referral links, affiliate links, or sponsored placements in this
repo, and there is no paid placement in the tables. Ranking is price and nothing
else. If that ever changes it will be at the top of the README, not buried here.
