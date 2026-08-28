# Full Token Due Diligence — 4-Step Workflow

Use this workflow before deciding to buy a token. Run all four steps in sequence.

**If the user wants a single 0-100 verdict number rather than the fields, use the `gmgn-contract-dd` skill instead** — it scores the same responses on documented thresholds and reports a coverage figure. This document is the field-by-field read.

## Step 1 — Get basic info

```bash
gmgn-cli token info --chain sol --address <token_address> --raw
```

Check: `price`, `liquidity`, `holder_count`, `wallet_tags_stat.smart_wallets`, `wallet_tags_stat.renowned_wallets`, `link.website` / `link.twitter_username` / `link.telegram`.

**Red flags**: all `link.*` social fields empty, very low liquidity (<$10k), zero `wallet_tags_stat.smart_wallets` and `renowned_wallets`.

## Step 2 — Check security

```bash
gmgn-cli token security --chain sol --address <token_address> --raw
```

**These are booleans and numbers, not strings.** Verified against live responses on 2026-08-28: `is_honeypot`, `is_open_source`, `is_renounced` and `is_blacklist` are `true` / `false` / `null` — comparing any of them against `"yes"` or `"no"` can never be true. `null` means GMGN reported nothing, which is **not** the same as `false`; on Solana `is_honeypot` and `is_open_source` are `null` by design. The integer mirrors `honeypot` / `open_source` / `renounced` are not a safe substitute either: USDC returns `honeypot: 0` alongside `is_honeypot: null`, so `0` conflates "no" with "unknown".

| Field | Safe | Warning | Danger |
|-------|------|---------|--------|
| `is_honeypot` | `false` | `null` → unknown, not safe | `true` → Do not buy |
| `is_open_source` | `true` | `null` → unknown (always `null` on SOL) | `false` |
| `is_renounced` | `true` | `null` → unknown | `false` |
| `is_blacklist` | `false` | `null` → unknown | `true` → can bar an address from trading |
| `renounced_mint` (SOL) | `true` | — | `false` → mint risk |
| `renounced_freeze_account` (SOL) | `true` | — | `false` → freeze risk |
| `buy_tax` / `sell_tax` | `"0"` | `0.01–0.05` | `>0.10` → high tax |
| `top_10_holder_rate` | `<0.20` | `0.20–0.40` | `>0.50` → whale risk |
| `burn_status` / `lock_summary.is_locked` | `"burn"` or `is_locked: true` | `""` → not reported | neither locked nor burned |

**Every rate and tax field is a decimal fraction**: `top_10_holder_rate: "0.1783"` is 17.83%, `buy_tax: "0.01"` is a 1% tax.

**A `0` in these fields is not automatically a pass.** `top_10_holder_rate` comes back as the string `"0"` on Solana and on some EVM tokens — 0% top-ten concentration does not exist, so read that as *not reported* and fall back to `token info` → `stat.top_10_holder_rate`. For the taxes the two spellings differ: `"0"` on a populated block is a genuine 0% tax, while `""` means the block was never populated and the tax is unknown. Reading either blank as a safe zero is how a token with no security record reads as clean.

**Three fields this table used to list are not returned by `token security` at all** — verified absent from every live response:

- `rug_ratio` — it is a `market trending` / `market trenches` row field, not a security field. Read it there.
- `creator_token_status` — it lives at `token info` → `dev.creator_token_status`.
- `sniper_count` — like `rug_ratio`, it is a `market trending` / `market trenches` row field, not a security field. From `token info` the nearest equivalent is `stat.top70_sniper_hold_rate`.

Also `owner_renounced` does not exist; the field is `is_renounced`.

## Step 3 — Check liquidity pool

```bash
gmgn-cli token pool --chain sol --address <token_address> --raw
```

Check: liquidity amount, which DEX (`exchange`), pool age (`creation_timestamp`). Low liquidity means high slippage risk when buying or selling.

## Step 4 — Check smart money signals

```bash
# Is smart money accumulating?
gmgn-cli token holders --chain sol --address <token_address> \
  --tag smart_degen --order-by buy_volume_cur --direction desc --limit 20 --raw

# Have KOLs already taken profit?
gmgn-cli token traders --chain sol --address <token_address> \
  --tag renowned --order-by profit --direction desc --limit 20 --raw
```

**Bullish signals**: smart_degen wallets buying heavily, unrealized_profit is large (still holding), renowned wallets accumulating, low sell_volume_cur.

**Bearish signals**: sell_volume_cur > buy_volume_cur for smart money, large realized profits already taken (they may be done), top holders with very high amount_percentage starting to sell.
