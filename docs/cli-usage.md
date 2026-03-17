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
| `--resolution` | Yes | Candlestick resolution: `1m` / `5m` / `15m` / `1h` / `4h` / `1d` |
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
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--interval` | Yes | `1h` / `3h` / `6h` / `24h` |
| `--limit` | No | Number of results (default 100, max 100) |
| `--order-by` | No | Sort field: `volume` / `swaps` / `liquidity` / `marketcap` / `holders` / `price` / `change` / `change1m` / `change5m` / `change1h` / `renowned_count` / `smart_degen_count` / `bluechip_owner_percentage` / `rank` / `creation_timestamp` / `square_mentions` / `history_highest_market_cap` / `gas_fee` |
| `--direction` | No | Sort direction: `asc` / `desc` (default `desc`) |
| `--filter` | No | Filter tag (repeatable): `has_social` / `not_risk` / `not_honeypot` / `verified` / `locked` / `renounced` / `distributed` / `frozen` / `burn` / `token_burnt` / `creator_hold` / `creator_close` / `creator_add_liquidity` / `creator_remove_liquidity` / `creator_sell` / `creator_buy` / `not_wash_trading` / `not_social_dup` / `not_image_dup` / `is_internal_market` / `is_out_market` |
| `--platform` | No | Platform filter (repeatable). Omit (or pass an empty list) to include **all** platforms. Available values depend on chain — see below. |

**`sol` platforms:** `Pump.fun` / `pump_mayhem` / `pump_mayhem_agent` / `pump_agent` / `letsbonk` / `bonkers` / `bags` / `memoo` / `liquid` / `bankr` / `zora` / `surge` / `anoncoin` / `moonshot_app` / `wendotdev` / `heaven` / `sugar` / `token_mill` / `believe` / `trendsfun` / `trends_fun` / `jup_studio` / `Moonshot` / `boop` / `xstocks` / `ray_launchpad` / `meteora_virtual_curve` / `pool_ray` / `pool_meteora` / `pool_pump_amm` / `pool_orca`

**`bsc` platforms:** `fourmeme` / `fourmeme_agent` / `bn_fourmeme` / `flap` / `clanker` / `lunafun` / `pool_uniswap` / `pool_pancake`

**`base` platforms:** `clanker` / `bankr` / `flaunch` / `zora` / `zora_creator` / `baseapp` / `basememe` / `virtuals_v2` / `klik`

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
  [--min-output <amount>] \
  [--anti-mev] \
  [--priority-fee <sol>] \
  [--tip-fee <amount>] \
  [--max-auto-fee <amount>] \
  [--gas-price <gwei>] \
  [--max-fee-per-gas <amount>] \
  [--max-priority-fee-per-gas <amount>] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` |
| `--from` | Yes | Wallet address (must match the wallet bound to the API Key) |
| `--input-token` | Yes | Input token contract address |
| `--output-token` | Yes | Output token contract address |
| `--amount` | No* | Input raw amount in minimal unit (e.g., lamports for SOL); required unless `--percent` is used |
| `--percent` | No* | Input amount as a percentage, e.g. `50` = 50%; required unless `--amount` is used; only valid when input token is not a currency (not SOL/BNB/ETH/USDC) |
| `--slippage` | No | Slippage tolerance, e.g. `0.01` = 1% |
| `--min-output` | No | Minimum output amount (raw amount) |
| `--anti-mev` | No | Enable anti-MEV protection (default true) |
| `--priority-fee` | No | Priority fee in SOL (≥ 0.00001 SOL, SOL only) |
| `--tip-fee` | No | Tip fee (SOL ≥ 0.00001 SOL / BSC ≥ 0.000001 BNB) |
| `--max-auto-fee` | No | Max automatic fee cap |
| `--gas-price` | No | Gas price in gwei (BSC ≥ 0.05 gwei / BASE/ETH ≥ 0.01 gwei) |
| `--max-fee-per-gas` | No | EIP-1559 max fee per gas (Base/ETH only) |
| `--max-priority-fee-per-gas` | No | EIP-1559 max priority fee per gas (Base/ETH only) |

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

---

## order get

Query order status. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
npx gmgn-cli order get --chain <chain> --order-id <order_id> [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `monad` |
| `--order-id` | Yes | Order ID (returned by the `swap` command) |

**Response fields (data):** Same structure as the `swap` response above.

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
| `AUTH_REPLAY_CHECK_UNAVAILABLE` | 503 | Anti-replay Redis unavailable (critical auth only) |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `TRADE_WALLET_MISMATCH` | 403 | `--from` address does not match the wallet bound to the API Key |
| `CHAIN_NOT_SUPPORTED` | 400 | Unsupported chain |
| `BAD_REQUEST` | 400 | Missing or invalid request parameters |
| `INTERNAL_API_UNAVAILABLE` | 502 | Downstream market API unavailable |
| `BROKER_UNAVAILABLE` | 502 | Downstream trade broker unavailable |
| `INTERNAL_ERROR` | 500 | Internal server error |
