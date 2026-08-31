# gmgn-cli Command Reference

## Global Options

All commands support `--raw`: output single-line JSON (useful for piping to `jq` or other tools).

---

## token info

Query token basic info (including realtime price).

```bash
npx gmgn-cli token info --chain <chain> --address <address> [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |

---

## token security

Query token security metrics (holder concentration, contract risks, etc.).

```bash
npx gmgn-cli token security --chain <chain> --address <address> [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |

---

## token pool

Query token liquidity pool info.

```bash
npx gmgn-cli token pool --chain <chain> --address <address> [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |

---

## token holders

Query top token holders list.

```bash
npx gmgn-cli token holders --chain <chain> --address <address> [--limit <n>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |
| `--limit` | No | Number of results (default 20, max 100) |

---

## token traders

Query top token traders list.

```bash
npx gmgn-cli token traders --chain <chain> --address <address> [--limit <n>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |
| `--limit` | No | Number of results (default 20, max 100) |

---

## market kline

Query token K-line (candlestick) data.

```bash
npx gmgn-cli market kline \
  --chain <chain> \
  --address <address> \
  --resolution <resolution> \
  [--from <unix_seconds>] \
  [--to <unix_seconds>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |
| `--resolution` | Yes | Candlestick resolution: `30s` / `1m` / `5m` / `15m` / `1h` / `4h` / `1d` |
| `--from` | No | Start time (Unix seconds) |
| `--to` | No | End time (Unix seconds) |

---

## market trending

Query trending token swap data.

```bash
npx gmgn-cli market trending \
  --chain <chain> \
  --interval <interval> \
  [--limit <n>] \
  [--order-by <field>] \
  [--direction asc|desc] \
  [--filter <tag>] \
  [--platform <name>] \
  [--min-<metric> <n>] [--max-<metric> <n>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | V1 supports `sol` / `bsc` / `base` / `eth` / `robinhood`; use `create-v2` for `arc` / `stable` |
| `--interval` | Yes | `1m` / `5m` / `1h` / `6h` / `24h` |
| `--limit` | No | Number of results (default 100, max 100) |
| `--order-by` | No | Sort field: `volume` / `swaps` / `liquidity` / `marketcap` / `holders` / `price` / `change` / `change1m` / `change5m` / `change1h` / `renowned_count` / `smart_degen_count` / `bluechip_owner_percentage` / `rank` / `creation_timestamp` / `square_mentions` / `history_highest_market_cap` / `gas_fee` |
| `--direction` | No | Sort direction: `asc` / `desc` (default `desc`) |
| `--filter` | No | Filter tag (repeatable): `has_social` / `not_risk` / `not_honeypot` / `verified` / `locked` / `renounced` / `distributed` / `frozen` / `burn` / `token_burnt` / `creator_hold` / `creator_close` / `creator_add_liquidity` / `creator_remove_liquidity` / `creator_sell` / `creator_buy` / `not_wash_trading` / `not_social_dup` / `not_image_dup` / `is_internal_market` / `is_out_market`. The gmgn web client also sends aliases `social_not_duplicate` / `img_not_duplicate` / `is_burnt` / `launching` / `migrated`, which are accepted but only the canonical tags change behavior. |
| `--platform` | No | Platform filter (repeatable). Omit (or pass an empty list) to include **all** platforms. Available values depend on chain — see below. |
| `--min-<metric>` / `--max-<metric>` | No | Numeric range filters (inclusive). Supported metrics: `volume` / `liquidity` / `marketcap` / `history-highest-marketcap` / `swaps` / `holder-count` / `gas-fee` / `renowned-count` / `smart-degen-count` / `bot-degen-count` / `visiting-count` / `price-change-percent` / `insider-rate` / `bundler-rate` / `entrapment-ratio` / `top10-holder-rate` / `top70-sniper-hold-rate` / `dev-team-hold-rate`. Unknown metrics are ignored by the service. |
| `--min-created` / `--max-created` | No | Token-age window, duration string with a `m` (minutes) / `h` (hours) / `d` (days) suffix, e.g. `30m` / `6h` / `7d`. `--min-created` is a minimum age (excludes younger tokens); `--max-created` a maximum age (excludes older tokens). The raw upstream rank interface accepts minutes only; the openapi-service does not forward this field — it evaluates the age window itself (cutoff = now − duration, native for `m`/`h`/`d`), so `6h`/`7d` work here. A bare number with no unit suffix is not accepted. |

**`sol` platforms:** `Pump.fun` / `pump_mayhem` / `pump_mayhem_agent` / `pump_agent` / `letsbonk` / `bonkers` / `bags` / `memoo` / `liquid` / `bankr` / `zora` / `surge` / `anoncoin` / `moonshot_app` / `wendotdev` / `heaven` / `sugar` / `token_mill` / `believe` / `trendsfun` / `trends_fun` / `jup_studio` / `Moonshot` / `boop` / `xstocks` / `ray_launchpad` / `meteora_virtual_curve` / `pool_ray` / `pool_meteora` / `pool_pump_amm` / `pool_orca`

**`bsc` platforms:** `fourmeme` / `fourmeme_agent` / `bn_fourmeme` / `flap` / `clanker` / `lunafun` / `pool_uniswap` / `pool_pancake`

**`base` platforms:** `clanker` / `bankr` / `flaunch` / `zora` / `zora_creator` / `baseapp` / `basememe` / `virtuals_v2` / `klik`

**`eth` platforms:** `trench` / `clanker` / `klik` / `livo` / `stroid` / `pool_uniswap_v2` / `pool_uniswap_v3` / `printr`

---

## portfolio holdings

Query wallet token holdings.

```bash
npx gmgn-cli portfolio holdings \
  --chain <chain> \
  --wallet <wallet_address> \
  [--limit <n>] \
  [--cursor <cursor>] \
  [--order-by <field>] \
  [--direction asc|desc] \
  [--sell-out] \
  [--show-small] \
  [--hide-abnormal] \
  [--hide-airdrop] \
  [--hide-closed] \
  [--hide-open] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--wallet` | Yes | Wallet address |
| `--limit` | No | Page size (default `20`, max 50) |
| `--cursor` | No | Pagination cursor |
| `--order-by` | No | Sort field: `usd_value` / `price` / `unrealized_profit` / `realized_profit` / `total_profit` / `history_bought_cost` / `history_sold_income` (default `usd_value`) |
| `--direction` | No | Sort direction: `asc` / `desc` (default `desc`) |
| `--sell-out` | No | Include sold-out positions |
| `--show-small` | No | Include small-value positions |
| `--hide-abnormal` | No | Hide abnormal positions |
| `--hide-airdrop` | No | Hide airdrop positions |
| `--hide-closed` | No | Hide closed positions |
| `--hide-open` | No | Hide open positions |

---

## portfolio activity

Query wallet transaction activity.

```bash
npx gmgn-cli portfolio activity \
  --chain <chain> \
  --wallet <wallet_address> \
  [--token <token_address>] \
  [--limit <n>] \
  [--cursor <cursor>] \
  [--type buy] [--type sell] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--wallet` | Yes | Wallet address |
| `--token` | No | Filter by token contract address |
| `--limit` | No | Page size |
| `--cursor` | No | Pagination cursor |
| `--type` | No | Activity type (repeatable): `buy` / `sell` / `add` / `remove` / `transfer` |

---

## portfolio stats

Query wallet trading statistics. Supports batch queries.

```bash
npx gmgn-cli portfolio stats \
  --chain <chain> \
  --wallet <wallet_address_1> [--wallet <wallet_address_2>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--wallet` | Yes | Wallet address (repeatable for batch queries) |

---

## portfolio profits

Batch query wallet profit and loss for 1–100 wallets.

```bash
gmgn-cli portfolio profits \
  --chain <chain> \
  --wallet <wallet_address_1> [--wallet <wallet_address_2>] \
  [--period 1d|7d|30d|all] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--wallet` | Yes | Wallet address (one or more, max 100) |
| `--period` | No | P&L period: `1d` / `7d` / `30d` / `all` (default `7d`) |

The response contains a `list` array with one result per wallet, including selected-period and all-time realized profit, unrealized profit, total profit, total cost, and buy/sell counts.

---

## portfolio info

Query wallets and main currency balances bound to the API Key.

```bash
npx gmgn-cli portfolio info [--raw]
```

No additional parameters required.

---

## portfolio token-balance

Query wallet token balance for a single token.

```bash
npx gmgn-cli portfolio token-balance \
  --chain <chain> \
  --wallet <wallet_address> \
  --token <token_address> \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--wallet` | Yes | Wallet address |
| `--token` | Yes | Token contract address |

---

## portfolio created-tokens

Query tokens created by a developer wallet.

```bash
npx gmgn-cli portfolio created-tokens \
  --chain <chain> \
  --wallet <wallet_address> \
  [--order-by <field>] \
  [--direction asc|desc] \
  [--migrate-state <state>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--wallet` | Yes | Developer wallet address |
| `--order-by` | No | Sort field: `market_cap` / `token_ath_mc` |
| `--direction` | No | Sort direction: `asc` / `desc` |
| `--migrate-state` | No | Filter: `migrated` / `non_migrated` |

---

## market trenches

Query Trenches token lists (new creation, near completion, completed).

```bash
npx gmgn-cli market trenches --chain <chain> [--type <type...>] [--launchpad-platform <platform...>] [--limit <n>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--type` | No | Categories to query, repeatable: `new_creation` / `near_completion` / `completed` (default: all three) |
| `--launchpad-platform` | No | Launchpad platform filter, repeatable (default: all platforms for the chain). Values depend on chain — see below. |
| `--limit` | No | Max results per category, max 80 (default: 80) |

**`sol` platforms:** `Pump.fun` / `pump_mayhem` / `pump_mayhem_agent` / `pump_agent` / `letsbonk` / `bonkers` / `bags` / `memoo` / `liquid` / `bankr` / `zora` / `surge` / `anoncoin` / `moonshot_app` / `wendotdev` / `heaven` / `sugar` / `token_mill` / `believe` / `trendsfun` / `trends_fun` / `jup_studio` / `Moonshot` / `boop` / `ray_launchpad` / `meteora_virtual_curve` / `xstocks`

**`bsc` platforms:** `fourmeme` / `fourmeme_agent` / `bn_fourmeme` / `four_xmode_agent` / `cubepeg` / `likwid` / `goplus_creator` / `goplus_skills` / `openfour` / `flap` / `flap_stocks` / `flap_aioracle` / `clanker` / `lunafun`

**`base` platforms:** `clanker` / `bankr` / `flaunch` / `zora` / `zora_creator` / `baseapp` / `basememe` / `virtuals_v2` / `klik`

**`eth` platforms:** `trench` / `clanker` / `klik` / `livo` / `stroid` / `pool_uniswap_v2` / `pool_uniswap_v3` / `printr`

**Response:** `data.new_creation`, `data.pump`, `data.completed` — each is an array of `RankItem` (same structure as `market trending` rank items). **Note: `data.pump` in the response corresponds to `--type near_completion` in the request. The API always returns this category under the key `pump`, not `near_completion`.**

---

## market signal

Query token signals — price spikes, smart money buys, large buys, Dex ads, CTO events, and more. Returns a list of `TokenSignalItem` sorted by `trigger_at` descending (most recent first). **Maximum 50 results per group.**

```bash
# Single group (individual flags):
gmgn-cli market signal --chain sol [--signal-type <n>...] [--mc-min <usd>] [--mc-max <usd>] [--raw]

# Multi-group override (JSON array):
gmgn-cli market signal --chain sol --groups '<json_array>' [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `robinhood` / `arc` / `stable` |
| `--signal-type` | No | Signal type(s), repeatable (1–21, default: all). See Signal Types below. |
| `--mc-min` | No | Min market cap at trigger time (USD) |
| `--mc-max` | No | Max market cap at trigger time (USD) |
| `--trigger-mc-min` | No | Min market cap at signal trigger moment (USD) |
| `--trigger-mc-max` | No | Max market cap at signal trigger moment (USD) |
| `--total-fee-min` | No | Min total fees paid (USD) |
| `--total-fee-max` | No | Max total fees paid (USD) |
| `--min-create-or-open-ts` | No | Min token creation or open timestamp (Unix seconds string) |
| `--max-create-or-open-ts` | No | Max token creation or open timestamp (Unix seconds string) |
| `--groups` | No | Multi-group JSON array — overrides all individual flags when provided |

**Signal Types:**

| Value | Name | Description |
|-------|------|-------------|
| 1 | SignalType1 | General signal (K-line price spike) |
| 2 | SignalTypeDexAd | Dex ad placement |
| 3 | SignalTypeDexUpdateLink | Dex social link updated |
| 4 | SignalTypeDexTrendingBar | Dex trending bar |
| 5 | SignalTypeDexBoost | Dex Boost |
| 6 | SignalTypePriceUp | Price spike |
| 7 | SignalTypePriceATH | All-time high price |
| 8 | SignalTypeMcpKeyLevel | Market cap key level |
| 9 | SignalTypeLive | Live stream |
| 10 | SignalTypeBundlerSell | Bundler sell |
| 11 | SignalTypeCto | Community takeover (CTO) |
| 12 | SignalTypeSmartDegenBuy | Smart money buy |
| 13 | SignalTypePlatformCall | Platform call |
| 14 | SignalTypeLargeAmountBuy | Large amount buy |
| 15 | SignalTypeMultiBuy | Multiple buys |
| 16 | SignalTypeMultiLargeBuy | Multiple large buys |
| 17 | SignalTypeBagsClaims | Bags Claim |
| 18 | SignalTypePumpClaims | Pump Claim |
| 19 | SignalTypePlatformCallV2 | Platform call (V2) |
| 20 | SignalTypeKOLBuy | KOL buy |
| 21 | SignalTypeBankerClaims | Banker Claim (Base chain Banker platform claim fee) |

---

## market hot-searches

Query the hot-search ranking — the most-searched tokens, ranked by `visiting_count` (search heat). Cross-chain top-500; one request can cover several chains at once. API Key auth only.

```bash
# Default 7-chain set (sol/bsc/base/eth/robinhood/arc/stable, each 24h):
gmgn-cli market hot-searches [--raw]

# Specific chain(s) and interval:
gmgn-cli market hot-searches --chain <chain...> [--interval <1m|5m|1h|6h|24h>] [--limit <n>] [--filter <tag...>] [--min-* <n>] [--max-* <n>] [--raw]

# Full per-param override (JSON array):
gmgn-cli market hot-searches --params '<json_array>' [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | No | Repeatable: `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable`. Omit for the default 7-chain set. |
| `--interval` | No | `1m` / `5m` / `1h` / `6h` / `24h` (default `24h`). Applies to every `--chain`. |
| `--limit` | No | Max results per chain (default `500`). |
| `--filter` | No | Repeatable **boolean** filter tags (downstream `filter.filters`). sol defaults: `renounced` / `frozen`; EVM defaults: `not_honeypot` / `verified` / `renounced`. Recognised tags: `renounced` / `frozen` (sol) / `is_burnt` / `token_burnt` / `not_wash_trading` / `not_honeypot` (EVM) / `verified` (EVM) / `locked` (EVM) / `has_social` / `distribed` / `not_risk` / `img_not_duplicate` / `social_not_duplicate` / `creator_hold` / `creator_close` / `dexscr_update_link` / `launching` / `migrated` / `hide_b20` (base) / `hide_non_b20` (base). Unknown tags are silent no-ops. |
| `--min-*` / `--max-*` | No | Numeric range bounds, **same metric names as `market trending`** (`--min-liquidity`, `--max-marketcap`, `--min-volume`, `--min-swaps`, `--min-smart-degen-count`, …, plus `--min-created`/`--max-created` durations). Translated server-side per `--interval`. `price_change_percent` only applies to `1m`/`5m`/`1h`. |
| `--params` | No | Full JSON array override — overrides `--chain` / `--interval` / `--limit` / `--filter` and range flags when provided. Filter fields are flattened onto each param (no nested `filter` object): a param accepts `filters`, `limit`, `min_created`/`max_created`, and rank-style `min_<metric>`/`max_<metric>` keys. |

**Response:** `data` is an array of `(interval, chain)` blocks; each block has `interval`, `chain`, `version`, and `tokens`. `tokens` uses the **same long-form fields as `market trending`** (`address`, `symbol`, `visiting_count`, `market_cap`, …) — the server maps the upstream shortcodes for you — and each token carries a 1-based `rank`. Ranked by search heat (`visiting_count`), max 500 per chain. **Note:** `--chain all` is not valid — pass `--chain` multiple times to aggregate across chains. Boolean tag names differ from `market trending`: this path uses `launching`/`migrated` and `img_not_duplicate`/`social_not_duplicate`.

---

## track follow-tokens

Query the followed token list for a wallet. Returns a paginated list of tokens the wallet has bookmarked on GMGN, with full market data. API Key auth only.

```bash
gmgn-cli track follow-tokens \
  --chain <chain> \
  --wallet <wallet_address> \
  [--group-id <id>] \
  [--order-by <field>] \
  [--direction <asc|desc>] \
  [--limit <n>] \
  [--cursor <cursor>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--wallet` | Yes | Wallet address |
| `--group-id` | No | `all_group` (all tokens), `default`, or a user-defined group ID |
| `--interval` | No | Time interval for price change stats: `1m` / `5m` / `1h` / `6h` / `24h` |
| `--order-by` | No | `created_at` / `swaps` / `volume` / `market_cap` / `liquidity` / `price` / `open_timestamp` |
| `--direction` | No | Sort direction: `asc` / `desc` |
| `--limit` | No | Page size |
| `--cursor` | No | Pagination cursor from previous response |
| `--search` | No | Search by token name or address |

---

## track follow-token-groups

Query the follow token group names for a wallet. Returns the groups a wallet uses to organise its followed tokens on GMGN. API Key auth only.

```bash
gmgn-cli track follow-token-groups \
  --chain <chain> \
  --wallet <wallet_address> \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--wallet` | Yes | Wallet address |

---

## portfolio follow-wallet

Query follow-wallet trade records. Returns trades from wallets you personally follow on the GMGN platform. The follow list is resolved automatically from the GMGN user account bound to the API Key — `--wallet` is optional. Signed auth (API Key + private key signature).

```bash
gmgn-cli track follow-wallet \
  --chain <chain> \
  [--wallet <wallet_address>] \
  [--limit <n>] \
  [--side <side>] \
  [--filter <tag>] \
  [--min-amount-usd <n>] \
  [--max-amount-usd <n>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--wallet` | No | Wallet address (optional; follow list resolved from API Key's bound user account) |
| `--limit` | No | Page size (1–100, default 10) |
| `--side` | No | Trade direction: `buy` / `sell` |
| `--filter` | No | Filter conditions (repeatable) |
| `--min-amount-usd` | No | Minimum trade amount (USD) |
| `--max-amount-usd` | No | Maximum trade amount (USD) |

---

## portfolio kol

Query KOL trade records.

```bash
gmgn-cli track kol [--chain <chain>] [--limit <n>] [--side <side>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | No | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` (default `sol`) |
| `--limit` | No | Page size (1–200, default 100) |
| `--side` | No | Filter by trade direction: `buy` / `sell` (client-side filter) |

---

## portfolio smartmoney

Query Smart Money trade records.

```bash
gmgn-cli track smartmoney [--chain <chain>] [--limit <n>] [--side <side>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | No | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` (default `sol`) |
| `--limit` | No | Page size (1–200, default 100) |
| `--side` | No | Filter by trade direction: `buy` / `sell` (client-side filter) |

---

## order quote

Get a swap quote without submitting a transaction. Uses normal auth — only `GMGN_API_KEY` is required, no `GMGN_PRIVATE_KEY` needed.

```bash
npx gmgn-cli order quote \
  --chain <chain> \
  --from <wallet_address> \
  --input-token <input_token_address> \
  --output-token <output_token_address> \
  --amount <input_amount> \
  --slippage <n> \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--from` | Yes | Wallet address |
| `--input-token` | Yes | Input token contract address |
| `--output-token` | Yes | Output token contract address |
| `--amount` | Yes | Input amount (smallest unit) |
| `--slippage` | Yes | Slippage tolerance as an integer 0–100, e.g. `30` = 30% |

**Response fields (data):**

| Field | Type | Description |
|-------|------|-------------|
| `input_token` | string | Input token contract address |
| `output_token` | string | Output token contract address |
| `input_amount` | string | Input amount (smallest unit) |
| `output_amount` | string | Expected output amount (smallest unit) |
| `min_output_amount` | string | Minimum output after slippage |
| `slippage` | number | Actual slippage percentage |

---

## swap

Submit a token swap. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
npx gmgn-cli swap \
  --chain <chain> \
  --from <wallet_address> \
  --input-token <input_token_address> \
  --output-token <output_token_address> \
  [--amount <input_amount> | --percent <pct>] \
  [--slippage <n>] \
  [--auto-slippage] \
  [--min-output <amount>] \
  [--anti-mev] \
  [--priority-fee <sol>] \
  [--tip-fee <amount>] \
  [--gas-price <gwei>] \
  [--max-fee-per-gas <amount>] \
  [--max-priority-fee-per-gas <amount>] \
  [--condition-orders <json>] \
  [--sell-ratio-type <buy_amount|hold_amount>] \
  [--raw]
```

| Option | Required | Chain | Description |
|--------|----------|-------|-------------|
| `--chain` | Yes | all | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--from` | Yes | all | Wallet address (must match the wallet bound to the API Key) |
| `--input-token` | Yes | all | Input token contract address |
| `--output-token` | Yes | all | Output token contract address |
| `--amount` | No* | all | Input raw amount in minimal unit (e.g., lamports for SOL); required unless `--percent` is used |
| `--percent` | No* | all | Input amount as a percentage, e.g. `50` = 50%; required unless `--amount` is used; only valid when input token is not a currency (not SOL/BNB/ETH/USDC) |
| `--slippage` | No | all | Slippage tolerance as an integer 0–100, e.g. `30` = 30% |
| `--auto-slippage` | No | all | Enable automatic slippage |
| `--min-output` | No | all | Minimum output amount (raw amount) |
| `--anti-mev` | No | all | Enable anti-MEV protection (default true) |
| `--priority-fee` | No | `sol` | Priority fee in SOL (≥ 0.00001) |
| `--tip-fee` | No | `sol` / `bsc` | Tip fee (SOL ≥ 0.00001 / BSC ≥ 0.000001 BNB) |
| `--gas-price` | No | `bsc` / `base` / `eth` | Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01) |
| `--gas-level` | No | `eth` | Gas price tier: `low` / `average` / `high`. Mutually exclusive with `--gas-price`. |
| `--auto-fee` | No | `eth` | **Only with `--condition-orders`.** GMGN automatically selects the optimal fee. |
| `--max-fee-per-gas` | No | `bsc` / `base` / `eth` | EIP-1559 max fee per gas |
| `--max-priority-fee-per-gas` | No | `bsc` / `base` / `eth` | EIP-1559 max priority fee per gas |
| `--condition-orders` | No | sol / bsc / base / eth / robinhood | JSON array of take-profit/stop-loss conditions attached after a successful swap (see example below). **Not supported on `arc` / `stable`.** |
| `--sell-ratio-type` | No | all | **Only with `--condition-orders`.** Sell ratio base: `buy_amount` (default) / `hold_amount` |

**`--condition-orders` example** (100% sell at 2× price, 100% sell at 50% price):

```json
[{"order_type":"profit_stop","side":"sell","price_scale":"100","sell_ratio":"100"},{"order_type":"loss_stop","side":"sell","price_scale":"50","sell_ratio":"100"}]
```

> Strategy creation is **best-effort**: if the swap succeeds but strategy creation fails, the swap result is still returned (with `strategy_order_id` absent). Only `order_type`, `side`, `price_scale`, and `sell_ratio` are accepted per condition — extra fields cause a 400 error.

**Response fields (data):**

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | Order ID for follow-up queries |
| `hash` | string | Transaction hash |
| `state` | int | Order state code |
| `confirmation.state` | string | `processed` / `confirmed` / `failed` / `expired` |
| `confirmation.detail` | string | Confirmation detail message |
| `error_code` | string | Error code on failure |
| `error_status` | string | Error description on failure |
| `height` | number | Block height of the transaction |
| `order_height` | number | Block height when the order was placed |
| `input_token` | string | Input token contract address |
| `output_token` | string | Output token contract address |
| `filled_input_amount` | string | Actual input consumed (smallest unit); empty if not filled |
| `filled_output_amount` | string | Actual output received (smallest unit); empty if not filled |
| `strategy_order_id` | string | Strategy order ID; only present when `--condition-orders` was passed and strategy creation succeeded |

---

## multi-swap

Submit token swaps across multiple wallets concurrently. Each wallet executes independently. Up to 100 wallets per request, all must be bound to the API Key. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
gmgn-cli multi-swap \
  --chain <chain> \
  --accounts <addr1>,<addr2> \
  --input-token <input_token_address> \
  --output-token <output_token_address> \
  [--input-amount <json>] \
  [--input-amount-bps <json>] \
  [--output-amount <json>] \
  [--slippage <n>] \
  [--auto-slippage] \
  [--anti-mev] \
  [--priority-fee <sol>] \
  [--tip-fee <amount>] \
  [--gas-price <gwei>] \
  [--max-fee-per-gas <amount>] \
  [--max-priority-fee-per-gas <amount>] \
  [--condition-orders <json>] \
  [--sell-ratio-type <buy_amount|hold_amount>] \
  [--raw]
```

| Option | Required | Chain | Description |
|--------|----------|-------|-------------|
| `--chain` | Yes | all | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--accounts` | Yes | all | Comma-separated wallet addresses (1–100, all bound to API Key) |
| `--input-token` | Yes | all | Input token contract address |
| `--output-token` | Yes | all | Output token contract address |
| `--input-amount` | No* | all | JSON map `{"addr":"amount"}` in smallest unit; one of the three amount fields is required |
| `--input-amount-bps` | No* | all | JSON map `{"addr":"bps"}` where 5000 = 50%; only valid when input token is not a currency |
| `--output-amount` | No* | all | JSON map `{"addr":"amount"}` target output in smallest unit |
| `--slippage` | No | all | Slippage tolerance as an integer 0–100, e.g. `30` = 30% |
| `--auto-slippage` | No | all | Enable automatic slippage |
| `--anti-mev` | No | all | Enable anti-MEV protection |
| `--priority-fee` | No | `sol` | Priority fee in SOL (≥ 0.00001) |
| `--tip-fee` | No | `sol` / `bsc` | Tip fee (SOL ≥ 0.00001 / BSC ≥ 0.000001 BNB) |
| `--gas-price` | No | `bsc` / `base` / `eth` | Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01) |
| `--gas-level` | No | `eth` | Gas price tier: `low` / `average` / `high`. Mutually exclusive with `--gas-price`. |
| `--auto-fee` | No | `eth` | **Only with `--condition-orders`.** GMGN automatically selects the optimal fee. |
| `--max-fee-per-gas` | No | `bsc` / `base` / `eth` | EIP-1559 max fee per gas |
| `--max-priority-fee-per-gas` | No | `bsc` / `base` / `eth` | EIP-1559 max priority fee per gas |
| `--condition-orders` | No | sol / bsc / base / eth / robinhood | JSON array of take-profit/stop-loss conditions, attached to each successful wallet's swap (best-effort). **Not supported on `arc` / `stable`.** |
| `--sell-ratio-type` | No | all | **Only with `--condition-orders`.** Sell ratio base: `buy_amount` (default) / `hold_amount` |

**Response fields (data):** Array of per-wallet results:

| Field | Type | Description |
|-------|------|-------------|
| `account` | string | Wallet address |
| `success` | bool | Whether this wallet's swap succeeded |
| `error` | string | Error message on failure |
| `error_code` | string | Error code on failure |
| `result` | object | OrderResponse on success (same fields as `swap` response) |
| `result.strategy_order_id` | string | Strategy order ID; only present when `--condition-orders` passed and strategy creation succeeded |

---

## order get

Query order status. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
npx gmgn-cli order get --chain <chain> --order-id <order_id> [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--order-id` | Yes | Order ID (returned by the `swap` command) |

**Response fields (data):** Same structure as the `swap` response above.

## order strategy create

Create a limit/strategy order. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
gmgn-cli order strategy create \
  --chain <chain> \
  --from <wallet_address> \
  --base-token <base_token_address> \
  --quote-token <quote_token_address> \
  --order-type <limit_order|smart_trade> \
  --sub-order-type <buy_low|buy_high|stop_loss|take_profit|mix_trade> \
  [--check-price <price>] \
  [--open-price <price>] \
  [--amount-in <amount> | --amount-in-percent <pct>] \
  [--slippage <n> | --auto-slippage] \
  [--limit-price-mode <exact|slippage>] \
  [--expire-in <seconds>] \
  [--sell-ratio-type <buy_amount|hold_amount>] \
  [--quote-investment <amount>] \
  [--condition-orders <json>] \
  [--priority-fee <sol>] \
  [--tip-fee <amount>] \
  [--gas-price <gwei>] \
  [--anti-mev] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--base-token` | Yes | Base token contract address |
| `--quote-token` | Yes | Quote token contract address |
| `--order-type` | Yes | Order type: `limit_order` / `smart_trade` |
| `--sub-order-type` | Yes | `limit_order`: `buy_low` / `buy_high` / `stop_loss` / `take_profit`; `smart_trade` with condition_orders: `mix_trade` |
| `--check-price` | No* | Trigger check price — required for `limit_order`; omit for `smart_trade` (trigger is in the `buy_low` condition order) |
| `--open-price` | No | Open price of the position |
| `--amount-in` | No* | Input amount (smallest unit); required unless `--amount-in-percent` is used |
| `--amount-in-percent` | No* | Input as percentage (e.g. `50` = 50%); required unless `--amount-in` is used |
| `--limit-price-mode` | No | `exact` / `slippage` (default: `slippage`) |
| `--expire-in` | No | Order expiry in seconds |
| `--sell-ratio-type` | No | `buy_amount` (default) / `hold_amount` |
| `--quote-investment` | No | Quote token investment amount (`smart_trade`) |
| `--condition-orders` | No | JSON array of condition sub-orders for `smart_trade`. Must include one `buy_low` entry (with `check_price` lower than `open_price`) plus at least one TP/SL entry. **Not supported on `arc` / `stable`** (`smart_trade` is rejected there). |
| `--slippage` | No | Slippage tolerance as an integer 0–100, e.g. `30` = 30% |
| `--auto-slippage` | No | Enable automatic slippage |
| `--priority-fee` | No | Priority fee in SOL (**required for SOL chain**) |
| `--tip-fee` | No | Tip fee (**required for SOL chain**) |
| `--gas-price` | No | Gas price in gwei (**required for BSC**; ≥ 0.05 / BASE/ETH ≥ 0.01) |
| `--anti-mev` | No | Enable anti-MEV protection |

> **Chain-specific fee requirements:**
> - **SOL:** `--priority-fee` and `--tip-fee` are both **required** (returns 400 if missing)
> - **BSC:** `--gas-price` is **required** (returns 400 if missing)
> - **ETH/BASE:** no required fee fields

**Response fields (data):**

| Field | Type | Description |
|-------|------|-------------|
| `order_id` | string | Created strategy order ID |
| `is_update` | bool | `true` if an existing order was updated |

---

## order strategy create-v2

Create a V2 smart-trade strategy through `POST /v2/trade/strategy/create`. It is independent from the V1 command.

```bash
gmgn-cli order strategy create-v2 \
  --chain <chain> --from <wallet> \
  --base-token <token> --quote-token <token> \
  --buy-type <market|limit|position> \
  --condition-orders <json-array> --sell-param <json-object> \
  [--quote-investment <amount>] [--buy-order <json-object>] \
  [--buy-param <json-object>] [--open-amount <amount>] \
  [--open-price <price>] [--cost-price <price>] \
  [--sell-ratio-type <buy_amount|hold_amount>] \
  [--limit-price-mode <exact|slippage>] [--expire-in <seconds>] [--raw]
```

Market and limit entries require `--quote-investment`; limit also requires `--buy-order`. Position entries require `--open-amount` and `--open-price`. All JSON options are parsed before submission.

## order strategy list

List strategy orders. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
gmgn-cli order strategy list --chain <chain> [--type <open|history>] [--from <address>] [--group-tag <tag>] [--base-token <address>] [--page-token <token>] [--limit <n>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--type` | No | `open` (default) / `history` |
| `--from` | No | Filter by wallet address |
| `--group-tag` | No | Filter by group: `LimitOrder` / `STMix` |
| `--base-token` | No | Filter by token address |
| `--page-token` | No | Pagination cursor from previous response |
| `--limit` | No | Results per page |

**Response fields (data):**

| Field | Type | Description |
|-------|------|-------------|
| `next_page_token` | string | Cursor for next page; empty when no more data |
| `total` | int | Total count (only when `--type open`) |
| `list` | array | Strategy order list |

---

## order strategy cancel

Cancel a strategy order. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
gmgn-cli order strategy cancel --chain <chain> --from <wallet_address> --order-id <id> [--order-type <type>] [--close-sell-model <model>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--order-id` | Yes | Order ID to cancel |
| `--order-type` | No | Order type: `limit_order` / `smart_trade` |
| `--close-sell-model` | No | Sell model when closing |

---

## cooking stats

Get token creation statistics grouped by launchpad.

```bash
gmgn-cli cooking stats [--raw]
```

No additional options required. Returns an array of `{ launchpad, token_count }` entries.

---

## cooking create

Create a token on a launchpad platform. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
gmgn-cli cooking create \
  --chain <chain> \
  --dex <dex> \
  --from <wallet_address> \
  --name <name> \
  --symbol <symbol> \
  --buy-amt <amount> \
  [--image <base64> | --image-url <url>] \
  [--slippage <n> | --auto-slippage] \
  [--website <url>] [--twitter <url>] [--telegram <url>] \
  [--fee <amount>] [--priority-fee <sol>] [--tip-fee <amount>] [--gas-price <amount>] \
  [--max-fee-per-gas <amount>] [--max-priority-fee-per-gas <amount>] \
  [--anti-mev] [--anti-mev-mode <off|normal|secure>] \
  [--raised-token <symbol>] \
  [--dev-wallet-bps <n>] [--dev-gas <amount>] [--dev-priority <amount>] [--dev-tip <amount>] [--dev-max-fee-per-gas <amount>] \
  [--approve-vision <v1|v2>] [--source <source>] \
  [--is-mayhem] [--is-cashback] [--is-buy-back] \
  [--pump-fee-share-list <json>] \
  [--flap-rate-conf <json>] \
  [--fourmeme-rate-conf <json>] \
  [--bags-fee-share-list <json>] \
  [--bonk-model <model>] \
  [--buy-wallets <json>] [--snip-buy-wallets <json>] \
  [--buy-trade-config <json>] [--sell-trade-config <json>] [--sell-configs <json>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `robinhood` |
| `--dex` | Yes | Launchpad per chain: `pump` / `bonk` / `bags` (sol), `fourmeme` / `flap` (bsc), `klik` / `clanker` (base), `trench` / `pons` (robinhood) |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--name` | Yes | Token name |
| `--symbol` | Yes | Token symbol |
| `--buy-amt` | Yes | Initial buy amount in native token (e.g. `0.01` SOL) |
| `--image` | No* | Token logo as base64-encoded data (max 2MB decoded); required unless `--image-url` is used |
| `--image-url` | No* | Token logo URL; required unless `--image` is used |
| `--slippage` | No* | Slippage tolerance as an integer 0–100, e.g. `30` = 30%; required unless `--auto-slippage` is used |
| `--auto-slippage` | No* | Enable automatic slippage; required unless `--slippage` is used |
| `--website` | No | Website URL |
| `--twitter` | No | Twitter link |
| `--telegram` | No | Telegram link |
| `--fee` | No | Base gas / fee |
| `--priority-fee` | No | Priority fee in SOL (**SOL only**, ≥ 0.0001 SOL) |
| `--tip-fee` | No | Tip fee (SOL ≥ 0.00001 / BSC ≥ 0.000001 BNB; ignored on BASE) |
| `--gas-price` | No | Gas price in wei (**EVM only**) |
| `--max-fee-per-gas` | No | Max fee per gas in wei (**EVM only**) |
| `--max-priority-fee-per-gas` | No | Max priority fee per gas in wei (**EVM only**) |
| `--anti-mev` | No | Enable anti-MEV protection (**SOL only**) |
| `--anti-mev-mode` | No | Anti-MEV mode: `off` / `normal` / `secure` (**SOL only**) |
| `--raised-token` | No | Raise token symbol: `pump`→`USDC`; `bonk`→`USD1`; `fourmeme`→`USDT`/`USD1`; `base`/`robinhood`→native only; omit for native |
| `--dev-wallet-bps` | No | Dev wallet fee share in basis points (100 = 1%) |
| `--dev-gas` | No | Dev gas amount |
| `--dev-priority` | No | Dev priority fee |
| `--dev-tip` | No | Dev tip fee |
| `--dev-max-fee-per-gas` | No | Dev tx feeCap in wei (**EVM EIP-1559**) |
| `--approve-vision` | No | Approve vision version: `v1` / `v2` (default: `v2`) |
| `--source` | No | Traffic source identifier |
| `--is-mayhem` | No | Enable Mayhem mode (**Pump.fun only**) |
| `--is-cashback` | No | Enable Cashback (**Pump.fun only**) |
| `--is-buy-back` | No | Enable Agent Auto Buyback (**Pump.fun only**) |
| `--pump-fee-share-list` | No | Fee share list as JSON array: `[{"provider":"twitter","username":"<handle>","basic_points":<n>}]` (**Pump.fun only**) |
| `--flap-rate-conf` | No | Rate config as JSON object (**Flap only**) |
| `--fourmeme-rate-conf` | No | Rate config as JSON object (**FourMeme only**) |
| `--bags-fee-share-list` | No | Fee share list as JSON array: `[{"provider":"twitter","username":"<handle>","basic_points":<n>}]` (**BAGS only**) |
| `--bonk-model` | No | Bonk model identifier (**bonk DEX only**) |
| `--buy-wallets` | No | Multi-wallet buy config as JSON array: `[{"from_address":"<addr>","buy_amt":"<n>"}]` |
| `--snip-buy-wallets` | No | Snipe-buy wallet config as JSON array: `[{"from_address":"<addr>","buy_amt":"<n>"}]` |
| `--buy-trade-config` | No | Buy-side trade config for CondMarket orders as JSON (TradeParam) |
| `--sell-trade-config` | No | Sell-side trade config for auto-sell / pending_sell as JSON (TradeParam) |
| `--sell-configs` | No | Auto-sell strategy list as JSON array (CookingSellConfig[]): `[{"sell_type":"delay_sell","delay_sec":<n>,"sell_ratio":"0.5","wallet_addresses":["<addr>"]}]` |

**Response fields (data):**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `pending` / `confirmed` / `failed` |
| `hash` | string | Transaction hash |
| `order_id` | string | Order ID for polling |
| `error_code` | string | Error code on failure |
| `error_status` | string | Error description on failure |

Token creation is asynchronous. Poll `order get` with the returned `order_id` if `status` is `pending`.

---

## Rate Limit Handling

All business routes are protected by GMGN's leaky-bucket limiter. Current production behavior is:

- `rate=10`, `capacity=10`
- every limited `429` response includes `X-RateLimit-Reset`
- `X-RateLimit-Reset` is a Unix timestamp in seconds, representing when the current cooldown is expected to end

CLI behavior:

- For read-only commands, `gmgn-cli` may wait until `X-RateLimit-Reset` and retry once automatically when the remaining cooldown is short.
- For longer cooldowns, or for `swap`, the CLI stops and prints the exact reset time instead of repeatedly sending requests.
- The auto-retry threshold defaults to `5000ms` and can be overridden with `GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS=<milliseconds>`.

Important notes:

- `RATE_LIMIT_EXCEEDED` and `RATE_LIMIT_BANNED` are request-frequency limits. Continuing to send requests during the cooldown can extend the ban by 5 seconds each time, up to 5 minutes.
- `ERROR_RATE_LIMIT_BLOCKED` is an error-count block on `POST /v1/trade/swap`. It is triggered by repeatedly hitting the same business error and should be treated as "fix the request first, then retry after reset".

---

## Error Codes

| Error | HTTP | Description |
|-------|------|-------------|
| `AUTH_KEY_INVALID` | 401 | API Key does not exist or has been deleted |
| `AUTH_IP_BLOCKED` | 403 | Request IP is not in the API Key whitelist |
| `AUTH_INVALID` | 401 | Auth info missing or invalid |
| `AUTH_SIGNATURE_INVALID` | 401 | Signature verification failed |
| `AUTH_TIMESTAMP_EXPIRED` | 401 | Timestamp is outside the valid window (±5s) |
| `AUTH_CLIENT_ID_REPLAYED` | 401 | client_id replayed within 7s |
| `AUTH_REPLAY_CHECK_UNAVAILABLE` | 503 | Anti-replay Redis unavailable (signed auth only) |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `RATE_LIMIT_BANNED` | 429 | Temporarily banned due to repeated rate limit violations |
| `ERROR_RATE_LIMIT_BLOCKED` | 429 | Temporarily blocked after repeated business errors on `swap` |
| `TRADE_WALLET_MISMATCH` | 403 | `--from` address does not match the wallet bound to the API Key |
| `CHAIN_NOT_SUPPORTED` | 400 | Unsupported chain |
| `BAD_REQUEST` | 400 | Missing or invalid request parameters |
| `INTERNAL_API_UNAVAILABLE` | 502 | Downstream market API unavailable |
| `BROKER_UNAVAILABLE` | 502 | Downstream trade broker unavailable |
| `TRADING_BOT_UNAVAILABLE` | 502 | Strategy order service temporarily unreachable |
| `INTERNAL_ERROR` | 500 | Internal server error |
