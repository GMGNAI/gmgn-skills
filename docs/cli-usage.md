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

## market trenches

Query Trenches token lists (new creation, near completion, completed).

```bash
npx gmgn-cli market trenches --chain <chain> [--type <type...>] [--launchpad-platform <platform...>] [--limit <n>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--type` | No | Categories to query, repeatable: `new_creation` / `near_completion` / `completed` (default: all three) |
| `--launchpad-platform` | No | Launchpad platform filter, repeatable (default: all platforms for the chain) |
| `--limit` | No | Max results per category, max 80 (default: 80) |

**Response:** `data.new_creation`, `data.pump`, `data.completed` — each is an array of `RankItem` (same structure as `market trending` rank items). **Note: `data.pump` in the response corresponds to `--type near_completion` in the request. The API always returns this category under the key `pump`, not `near_completion`.**

---

## portfolio follow-wallet

Query follow-wallet trade records.

```bash
npx gmgn-cli portfolio follow-wallet \
  --chain <chain> \
  [--wallet <wallet_address>] \
  [--base-token <token_address>] \
  [--page-token <cursor>] \
  [--limit <n>] \
  [--side <side>] \
  [--cost <cost>] \
  [--filter <tag>] \
  [--with-balance] \
  [--with-security] \
  [--min-amount-usd <n>] \
  [--max-amount-usd <n>] \
  [--is-gray] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` |
| `--wallet` | No | Filter by wallet address |
| `--base-token` | No | Filter by base token address |
| `--page-token` | No | Pagination cursor |
| `--limit` | No | Page size (1–200, default 100) |
| `--side` | No | Trade direction filter |
| `--cost` | No | Cost filter |
| `--filter` | No | Filter conditions (repeatable) |
| `--with-balance` | No | Include balance in response |
| `--with-security` | No | Include security info in response |
| `--min-amount-usd` | No | Minimum trade amount (USD) |
| `--max-amount-usd` | No | Maximum trade amount (USD) |
| `--is-gray` | No | Gray mode filter |

---

## portfolio kol

Query KOL trade records (SOL chain).

```bash
npx gmgn-cli portfolio kol [--limit <n>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--limit` | No | Page size (1–200, default 100) |

---

## portfolio smartmoney

Query Smart Money trade records (SOL chain).

```bash
npx gmgn-cli portfolio smartmoney [--limit <n>] [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--limit` | No | Page size (1–200, default 100) |

---

## order quote

Get a swap quote without submitting a transaction. `sol` / `base` use normal auth (API Key only). `bsc` uses critical auth and requires `GMGN_PRIVATE_KEY`.

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
| `--chain` | Yes | `sol` / `bsc` / `base` (`bsc` quote requires `GMGN_PRIVATE_KEY`) |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--input-token` | Yes | Input token contract address |
| `--output-token` | Yes | Output token contract address |
| `--amount` | Yes | Input amount (smallest unit) |
| `--slippage` | Yes | Slippage tolerance, e.g. `0.01` = 1% |

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
  [--max-auto-fee <amount>] \
  [--gas-price <gwei>] \
  [--max-fee-per-gas <amount>] \
  [--max-priority-fee-per-gas <amount>] \
  [--condition-orders <json>] \
  [--sell-ratio-type <buy_amount|hold_amount>] \
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
| `--auto-slippage` | No | Enable automatic slippage |
| `--min-output` | No | Minimum output amount (raw amount) |
| `--anti-mev` | No | Enable anti-MEV protection (default true) |
| `--priority-fee` | No | Priority fee in SOL (≥ 0.00001 SOL, SOL only) |
| `--tip-fee` | No | Tip fee (SOL ≥ 0.00001 SOL / BSC ≥ 0.000001 BNB) |
| `--max-auto-fee` | No | Max automatic fee cap |
| `--gas-price` | No | Gas price in gwei (BSC ≥ 0.05 gwei / BASE/ETH ≥ 0.01 gwei) |
| `--max-fee-per-gas` | No | EIP-1559 max fee per gas (Base/ETH only) |
| `--max-priority-fee-per-gas` | No | EIP-1559 max priority fee per gas (Base/ETH only) |
| `--condition-orders` | No | JSON array of take-profit/stop-loss conditions attached after a successful swap (see example below); only `profit_stop` and `loss_stop` are supported |
| `--sell-ratio-type` | No | Sell ratio base for `--condition-orders`: `buy_amount` (default) / `hold_amount` |

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

## order strategy create

Create a limit/strategy order. **Requires `GMGN_PRIVATE_KEY` configured in `.env`.**

```bash
gmgn-cli order strategy create \
  --chain <chain> \
  --from <wallet_address> \
  --base-token <base_token_address> \
  --quote-token <quote_token_address> \
  --order-type <limit_order> \
  --sub-order-type <buy_low|buy_high|stop_loss|take_profit> \
  --check-price <price> \
  [--amount-in <amount> | --amount-in-percent <pct>] \
  [--slippage <n> | --auto-slippage] \
  [--limit-price-mode <exact|slippage>] \
  [--expire-in <seconds>] \
  [--sell-ratio-type <buy_amount|hold_amount>] \
  [--priority-fee <sol>] \
  [--tip-fee <amount>] \
  [--gas-price <gwei>] \
  [--anti-mev] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--base-token` | Yes | Base token contract address |
| `--quote-token` | Yes | Quote token contract address |
| `--order-type` | Yes | Order type: `limit_order` |
| `--sub-order-type` | Yes | Sub-order type: `buy_low` / `buy_high` / `stop_loss` / `take_profit` |
| `--check-price` | Yes | Trigger check price |
| `--amount-in` | No* | Input amount (smallest unit); required unless `--amount-in-percent` is used |
| `--amount-in-percent` | No* | Input as percentage (e.g. `50` = 50%); required unless `--amount-in` is used |
| `--limit-price-mode` | No | `exact` / `slippage` (default: `slippage`) |
| `--expire-in` | No | Order expiry in seconds |
| `--sell-ratio-type` | No | `buy_amount` (default) / `hold_amount` |
| `--slippage` | No | Slippage tolerance, e.g. `0.01` = 1% |
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
  [--priority-fee <sol>] [--tip-fee <amount>] [--gas-price <amount>] \
  [--anti-mev] \
  [--raw]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` / `eth` / `ton` |
| `--dex` | Yes | Launchpad: `pump` / `raydium` / `pancakeswap` / `flap` / `fourmeme` / `bonk` / `bags` / ... |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--name` | Yes | Token name |
| `--symbol` | Yes | Token symbol |
| `--buy-amt` | Yes | Initial buy amount in native token (e.g. `0.01` SOL) |
| `--image` | No* | Token logo as base64-encoded data (max 2MB decoded); required unless `--image-url` is used |
| `--image-url` | No* | Token logo URL; required unless `--image` is used |
| `--website` | No | Website URL |
| `--twitter` | No | Twitter link |
| `--telegram` | No | Telegram link |
| `--slippage` | No | Slippage tolerance, e.g. `0.01` = 1% |
| `--auto-slippage` | No | Enable automatic slippage |
| `--priority-fee` | No | Priority fee in SOL (SOL only) |
| `--tip-fee` | No | Tip fee |
| `--gas-price` | No | Gas price in wei (EVM chains) |
| `--anti-mev` | No | Enable anti-MEV protection |

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
| `AUTH_REPLAY_CHECK_UNAVAILABLE` | 503 | Anti-replay Redis unavailable (critical auth only) |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `RATE_LIMIT_BANNED` | 429 | Temporarily banned due to repeated rate limit violations |
| `ERROR_RATE_LIMIT_BLOCKED` | 429 | Temporarily blocked after repeated business errors on `swap` |
| `TRADE_WALLET_MISMATCH` | 403 | `--from` address does not match the wallet bound to the API Key |
| `CHAIN_NOT_SUPPORTED` | 400 | Unsupported chain |
| `BAD_REQUEST` | 400 | Missing or invalid request parameters |
| `INTERNAL_API_UNAVAILABLE` | 502 | Downstream market API unavailable |
| `BROKER_UNAVAILABLE` | 502 | Downstream trade broker unavailable |
| `TRADING_BOT_UNAVAILABLE` | 502 | Trading bot service unreachable (strategy endpoints) |
| `INTERNAL_ERROR` | 500 | Internal server error |
