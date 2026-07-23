# Price history

One JSON line per collector run. Each line holds the cheapest on-demand price per
GPU key per provider at that moment. Append only. Nothing here is ever rewritten.

## Two schemas, kept apart on purpose

```
data/history/*.jsonl      schema 1, frozen, no new lines are added
data/history/v2/*.jsonl   schema 2, current
```

Schema 2 changed what a `gpu_key` is. In schema 1 the key was family plus VRAM,
so `H100 80GB` covered both the SXM part and the PCIe part. Those are not the
same product and the merge could hand a cheapest match a PCIe card when the job
needed SXM. In schema 2 the form is part of the key: `H100 80GB SXM`,
`H100 80GB PCIe`, `H100 94GB NVL`, and `H100 80GB (form unstated)` for a listing
whose form the provider never states.

The old lines were not migrated, and that is deliberate. A schema 1 line records
one cheapest price for `H100 80GB` across a mix of SXM and PCIe listings. There
is no way to work out afterwards which form that number belonged to, so any
migration would have to invent the answer. Rewriting an append only store with a
guessed value is worse than leaving a labelled boundary, so the schema 1 lines
stay exactly as they were written and schema 2 starts a fresh directory.

Every schema 2 line carries `"schema_version": 2`. Schema 1 lines have no such
field. Do not concatenate the two into a single time series. Read them as two
series that meet at the boundary.

## Line shape (schema 2)

```json
{
  "schema_version": 2,
  "collected_at": "2026-07-23T21:36:04+00:00",
  "cheapest": {
    "runpod": {"H100 80GB SXM": 2.69, "H100 80GB PCIe": 1.99},
    "vastai": {"H100 80GB SXM": 1.7449}
  }
}
```

Only on-demand prices with a real per GPU rate go in. Spot, reserved and
fractional GPU plans are in `data/prices.json` but not in this file.
