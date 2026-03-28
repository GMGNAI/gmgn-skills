# Full Token Due Diligence — 4-Step Workflow

Use this workflow before deciding to buy a token. Run all four steps in sequence.

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

Check these fields and their safe thresholds:

| Field | Safe | Warning | Danger |
|-------|------|---------|--------|
| `is_honeypot` | `"no"` | — | `"yes"` → Do not buy |
| `open_source` | `"yes"` | `"unknown"` | `"no"` |
| `owner_renounced` | `"yes"` | `"unknown"` | `"no"` |
| `renounced_mint` (SOL) | `true` | — | `false` → mint risk |
| `renounced_freeze_account` (SOL) | `true` | — | `false` → freeze risk |
| `buy_tax` / `sell_tax` | `0` | `0.01–0.05` | `>0.10` → high tax |
| `top_10_holder_rate` | `<0.20` | `0.20–0.40` | `>0.50` → whale risk |
| `rug_ratio` | `<0.10` | `0.10–0.30` | `>0.30` → high rug risk |
| `creator_token_status` | `creator_close` | — | `creator_hold` → dev not sold |
| `sniper_count` | `<5` | `5–20` | `>20` → heavily sniped |

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
