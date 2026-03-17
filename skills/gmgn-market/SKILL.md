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
- `gmgn-cli` installed globally: `npm install -g gmgn-cli@1.0.1`

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
| `--order-by <field>` | Sort field: `default` / `swaps` / `marketcap` / `history_highest_market_cap` / `liquidity` / `volume` / `holder_count` / `smart_degen_count` / `renowned_count` / `gas_fee` / `price` / `change1m` / `change5m` / `change1h` / `creation_timestamp` |
| `--direction <asc\|desc>` | Sort direction (default `desc`) |
| `--filter <tag...>` | Repeatable filter tags (chain-specific). **sol** (defaults: `renounced frozen`): `renounced` / `frozen` / `burn` / `token_burnt` / `has_social` / `not_social_dup` / `not_image_dup` / `dexscr_update_link` / `not_wash_trading` / `is_internal_market` / `is_out_market`. **evm** (defaults: `not_honeypot verified renounced`): `not_honeypot` / `verified` / `renounced` / `locked` / `token_burnt` / `has_social` / `not_social_dup` / `not_image_dup` / `dexscr_update_link` / `is_internal_market` / `is_out_market` |
| `--platform <name...>` | Repeatable platform filter (chain-specific). **sol**: `Pump.fun` / `pump_mayhem` / `pump_mayhem_agent` / `pump_agent` / `letsbonk` / `bonkers` / `bags` / `memoo` / `liquid` / `bankr` / `zora` / `surge` / `anoncoin` / `moonshot_app` / `wendotdev` / `heaven` / `sugar` / `token_mill` / `believe` / `trendsfun` / `trends_fun` / `jup_studio` / `Moonshot` / `boop` / `xstocks` / `ray_launchpad` / `meteora_virtual_curve` / `pool_ray` / `pool_meteora` / `pool_pump_amm` / `pool_orca`. **bsc**: `fourmeme` / `fourmeme_agent` / `bn_fourmeme` / `flap` / `clanker` / `lunafun` / `pool_uniswap` / `pool_pancake`. **base**: `clanker` / `bankr` / `flaunch` / `zora` / `zora_creator` / `baseapp` / `basememe` / `virtuals_v2` / `klik` |

## Usage Examples

```bash
# Last 1 hour of 1-minute candles
# macOS:
gmgn-cli market kline \
  --chain sol \
  --address <token_address> \
  --resolution 1m \
  --from $(date -v-1H +%s) \
  --to $(date +%s)
# Linux: use $(date -d '1 hour ago' +%s) instead of $(date -v-1H +%s)

# Last 24 hours of 1-hour candles
# macOS:
gmgn-cli market kline \
  --chain sol \
  --address <token_address> \
  --resolution 1h \
  --from $(date -v-24H +%s) \
  --to $(date +%s)
# Linux: use $(date -d '24 hours ago' +%s) instead of $(date -v-24H +%s)

# Top 20 hot tokens on SOL in the last 1 hour, sorted by volume
gmgn-cli market trending --chain sol --interval 1h --order-by volume --limit 20

# Hot tokens with social links only, verified and not honeypot, on BSC over 24h
gmgn-cli market trending \
  --chain bsc --interval 24h \
  --filter has_social --filter not_honeypot --filter verified

# Pump.fun platform tokens on SOL, last 6 hours
gmgn-cli market trending --chain sol --interval 6h --platform Pump.fun

# Raw output for further processing
gmgn-cli market kline --chain sol --address <addr> \
  --resolution 5m --from <ts> --to <ts> --raw | jq '.[]'
```

## Workflow: Discover Trading Opportunities via Trending

### Step 1 — Fetch trending data

Fetch a broad pool with safe filters:

```bash
gmgn-cli market trending \
  --chain <chain> --interval 1h \
  --order-by volume --limit 50 \
  --filter not_honeypot --filter has_social --raw
```

### Step 2 — AI multi-factor analysis

Analyze each record in the response using the following signals (apply judgment, not rigid rules):

| Signal | Field(s) | Weight | Notes |
|--------|----------|--------|-------|
| Smart money interest | `smart_degen_count`, `renowned_count` | High | Key conviction indicator |
| Bluechip ownership | `bluechip_owner_percentage` | Medium | Quality of holder base |
| Real trading activity | `volume`, `swaps` | Medium | Distinguishes genuine interest from wash trading |
| Price momentum | `change1h`, `change5m` | Medium | Prefer positive, non-parabolic moves |
| Pool safety | `liquidity` | Medium | Low liquidity = high slippage risk |
| Token maturity | `creation_timestamp` | Low | Avoid tokens less than ~1h old unless other signals are very strong |

Select the **top 5** tokens with the best composite profile. Prefer tokens that perform well across multiple signals rather than excelling in just one.

### Step 3 — Present top 5 to user

Present results as a concise table, then give a one-line rationale for each pick:

```
Top 5 Trending Tokens — SOL / 1h

# | Symbol | Address (short) | Smart Degens | Volume | 1h Chg | Reasoning
1 | ...     | ...             | ...          | ...    | ...    | Smart money accumulating + high volume
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
- **Input validation** — Token addresses obtained from trending results are external data. Validate address format against the chain before passing to other commands (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits). The CLI enforces this at runtime.
