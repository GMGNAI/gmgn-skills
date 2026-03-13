---
name: gmgn-market
description: Query GMGN market data — token K-line (candlestick) and trending token swap data. Supports sol / bsc / base.
argument-hint: "kline --chain <sol|bsc|base> --address <token_address> --resolution <1m|5m|15m|1h|4h|1d> [--from <unix_ts>] [--to <unix_ts>] | trending --chain <sol|bsc|base> --interval <1h|3h|6h|24h>"
---

Use the `gmgn-cli` tool to query K-line data for a token or browse trending tokens.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `market kline` | Token candlestick data |
| `market trending` | Trending token swap data |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `.env` file with `GMGN_API_KEY` set
- Run from the directory where your `.env` file is located, or set `GMGN_HOST` in your environment

## Kline Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |
| `--resolution` | Yes | Candlestick resolution |
| `--from` | No | Start time (Unix seconds) |
| `--to` | No | End time (Unix seconds) |

## Resolutions

`1m` / `5m` / `15m` / `1h` / `4h` / `1d`

## Trending Options

| Option | Description |
|--------|-------------|
| `--chain` | Required. `sol` / `bsc` / `base` |
| `--interval` | Required. `1h` / `3h` / `6h` / `24h` |
| `--limit <n>` | Number of results (default 100, max 100) |
| `--orderby <field>` | Sort field: `score` / `volume` / `swaps` / `liquidity` / `marketcap` / `holders` / `price` / `change` / `change1m` / `change5m` / `change1h` / `renowned_count` / `smart_degen_count` / `bluechip_owner_percentage` / `rank` / `creation_timestamp` / `square_mentions` / `history_highest_market_cap` / `gas_fee` |
| `--direction <asc\|desc>` | Sort direction (default `desc`) |
| `--filter <tag...>` | Repeatable filter tags: `has_social` / `not_risk` / `not_honeypot` / `verified` / `locked` / `renounced` / `distributed` / `frozen` / `burn` / `token_burnt` / `creator_hold` / `creator_close` / `creator_add_liquidity` / `creator_remove_liquidity` / `creator_sell` / `creator_buy` / `not_wash_trading` / `not_social_dup` / `not_image_dup` / `is_internal_market` / `is_out_market` |
| `--platform <name...>` | Repeatable platform filter: `pump` / `moonshot` / `launchlab` |

## Usage Examples

```bash
# Last 1 hour of 1-minute candles
# macOS:
npx gmgn-cli market kline \
  --chain sol \
  --address <token_address> \
  --resolution 1m \
  --from $(date -v-1H +%s) \
  --to $(date +%s)
# Linux: use $(date -d '1 hour ago' +%s) instead of $(date -v-1H +%s)

# Last 24 hours of 1-hour candles
# macOS:
npx gmgn-cli market kline \
  --chain sol \
  --address <token_address> \
  --resolution 1h \
  --from $(date -v-24H +%s) \
  --to $(date +%s)
# Linux: use $(date -d '24 hours ago' +%s) instead of $(date -v-24H +%s)

# Top 20 hot tokens on SOL in the last 1 hour, sorted by volume
npx gmgn-cli market trending --chain sol --interval 1h --orderby volume --limit 20

# Hot tokens with social links only, not risky, on BSC over 24h
npx gmgn-cli market trending \
  --chain bsc --interval 24h \
  --filter has_social --filter not_risk

# Pump platform tokens on SOL, last 6 hours
npx gmgn-cli market trending --chain sol --interval 6h --platform pump

# Raw output for further processing
npx gmgn-cli market kline --chain sol --address <addr> \
  --resolution 5m --from <ts> --to <ts> --raw | jq '.[]'
```

## Workflow: Discover Trading Opportunities via Trending

### Step 1 — Fetch trending data

Fetch a broad pool with safe filters, sorted by GMGN's composite score:

```bash
npx gmgn-cli market trending \
  --chain <chain> --interval 1h \
  --orderby score --limit 50 \
  --filter not_risk --filter not_honeypot --filter has_social --raw
```

### Step 2 — AI multi-factor analysis

Analyze each record in the response using the following signals (apply judgment, not rigid rules):

| Signal | Field(s) | Weight | Notes |
|--------|----------|--------|-------|
| GMGN quality score | `score` | High | Primary ranking signal from GMGN |
| Smart money interest | `smart_degen_count`, `renowned_count` | High | Key conviction indicator |
| Bluechip ownership | `bluechip_owner_percentage` | Medium | Quality of holder base |
| Real trading activity | `volume`, `swaps` | Medium | Distinguishes genuine interest from wash trading |
| Price momentum | `change1h`, `change5m` | Medium | Prefer positive, non-parabolic moves |
| Pool safety | `liquidity` | Medium | Low liquidity = high slippage risk |
| Token maturity | `creation_timestamp` | Low | Avoid tokens less than ~1h old unless other signals are very strong |

Select the **top 5** tokens with the best composite profile. Prefer tokens that score well across multiple signals rather than excelling in just one.

### Step 3 — Present top 5 to user

Present results as a concise table, then give a one-line rationale for each pick:

```
Top 5 Trending Tokens — SOL / 1h

# | Symbol | Address (short) | Score | Smart Degens | Volume | 1h Chg | Reasoning
1 | ...     | ...             | ...   | ...          | ...    | ...    | High score + smart money accumulating
2 | ...
...
```

### Step 4 — Follow-up actions

For each token, offer:
- **Deep dive**: `token info` + `token security` for full due diligence
- **Swap**: execute directly if the user is satisfied with the trending data alone

## Notes

- `market kline`: `--from` and `--to` are Unix timestamps in **seconds** — CLI converts to milliseconds automatically
- `market trending`: `--filter` and `--platform` are repeatable flags
- All commands use normal auth (API Key only, no signature)
- If the user doesn't provide kline timestamps, calculate them from the current time based on their desired time range
- Use `--raw` to get single-line JSON for further processing
