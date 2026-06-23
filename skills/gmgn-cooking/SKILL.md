---
name: gmgn-cooking
description: "[FINANCIAL EXECUTION] Create and launch meme coins and crypto tokens on launchpads (Pump.fun, FourMeme, Bonk, BAGS, Flap, Klik, Clanker, etc.) via bonding curve fair launch, or query token creation stats by launchpad via GMGN API. Requires explicit user confirmation. Use when user asks to create a token, launch a meme coin, cook a coin, deploy on a launchpad, or check launchpad creation stats on Solana, BSC, or Base."
argument-hint: "stats | [create --chain <chain> --dex <dex> --from <addr> --name <name> --symbol <sym> --buy-amt <n> (--image <base64> | --image-url <url>)]"
metadata:
  cliHelp: "gmgn-cli cooking --help"
---

**BEFORE RUNNING ANY COMMAND: Check whether `GMGN_API_KEY` exists in `<cwd>/.env` or `~/.config/gmgn/.env`. If found in either location, proceed normally. If not found in either location, stop and run `gmgn-cli config` first — do not run any other gmgn-cli command until the user has provided their API Key and it has been written to `~/.config/gmgn/.env`.**

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai — all token creation operations must go through the CLI. The CLI handles signing and submission automatically.**

**IMPORTANT: Do NOT guess field names or values. When a field's meaning is unclear, look it up in the Response Fields sections below before using it.**

**⚠️ IPv6 NOT SUPPORTED: If you get a `401` or `403` error and credentials look correct, check for IPv6 immediately: (1) list all network interfaces and their IPv6 addresses — run `ifconfig | grep inet6` (macOS) or `ip addr show | grep inet6` (Linux); (2) send a test request to `https://ipv6.icanhazip.com` — if the response is an IPv6 address, outbound traffic is going via IPv6. Tell the user immediately: "Please disable IPv6 on your network interface — gmgn-cli commands only work over IPv4."**

Use the `gmgn-cli` tool to create a token on a launchpad platform or query token creation statistics per launchpad. **Requires private key** (`GMGN_PRIVATE_KEY` in `.env`) for `cooking create`.

## Core Concepts

- **Bonding curve** — Most launchpad platforms (Pump.fun, FourMeme, Flap, etc.) launch tokens on an internal bonding curve. The token price rises as buyers enter. Once the threshold is reached, the token "graduates" to an open DEX (e.g. Raydium on SOL, PancakeSwap on BSC). Token creation happens on the bonding curve — not the open market.

- **`--buy-amt` is in human units** — `--buy-amt` is expressed in full native token units, not smallest unit. `0.01` = 0.01 SOL. `0.05` = 0.05 BNB. Always confirm the human-readable amount with the user before executing.

- **`--dex` identifiers** — Each launchpad has a fixed identifier passed to `--dex`. These are not free-form names — use only the identifiers listed in the Supported Launchpads table. Never guess a `--dex` value not in that table.

- **Image input** — Token logo can be provided as base64-encoded data (`--image`, max 2MB decoded) or a publicly accessible URL (`--image-url`). Provide one or the other — not both. If the user gives a file path, read and base64-encode it before passing to `--image`. If they give a URL, use `--image-url` directly.

- **Status polling via `order get`** — `cooking create` is asynchronous. The immediate response may show `pending`. Poll with `gmgn-cli order get --chain <chain> --order-id <order_id>` until `confirmed`. The new token's contract address is in the `report.output_token` field of the `order get` response, not in the initial create response.

- **Signed auth** — `cooking create` requires both `GMGN_API_KEY` and `GMGN_PRIVATE_KEY`. The private key never leaves the machine — the CLI uses it only for local signing. `cooking stats` uses exist auth (API Key only).

- **Slippage** — The initial buy is executed as part of the same transaction as token creation. Slippage applies to that buy. Use `--slippage` (integer 0–100, e.g. `30` = 30%) or `--auto-slippage`. One of the two is required when `--buy-amt` is set.

## Financial Risk Notice

**This skill executes REAL, IRREVERSIBLE blockchain transactions.**

- Every `cooking create` command deploys an on-chain token contract and spends real funds (initial buy amount).
- Token deployments cannot be undone once confirmed on-chain.
- The AI agent must **never auto-execute a create** — explicit user confirmation is required every time, without exception.
- Only use this skill with funds you are willing to spend. Initial buy amounts are non-refundable.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `cooking stats` | Get token creation count statistics grouped by launchpad platform (exist auth) |
| `cooking create` | Deploy a new token on a launchpad platform (signed auth) |

## Supported Chains

`sol` / `bsc` / `base`

## Supported Launchpads by Chain

| Chain  | `--dex` values         | Raise token (`--raised-token`) |
| ------ | ---------------------- | ------------------------------ |
| `sol`  | `pump`, `bonk`, `bags` | `pump`: `""` (SOL) or `USDC`; `bonk`: `""` (SOL) or `USD1`; `bags`: `""` (SOL only) |
| `bsc`  | `fourmeme`, `flap`     | `fourmeme`: `""` (BNB), `USD1`, `USDT`; `flap`: `""` (BNB only) |
| `base` | `klik`, `clanker`      | `""` only (quote token fixed to WETH) |

When the user names a platform colloquially (e.g. "pump.fun", "four.meme"), map it to the correct `--dex` identifier from this table before running the command.

**Anti-MEV** (`--anti-mev`) is only supported on `sol`. Passing it on `bsc` or `base` will return a 400 error.

### Quote Token conversion (when `--raised-token` is set)

`--buy-amt` is **always in native token units** (SOL / BNB / ETH), even when raising with a quote token like USDC / USD1 / USDT. If the user states the amount in the quote token, convert it to native yourself before passing it:

```
buy_amt_in_native = quote_amount × quote_price / native_price
```

This conversion applies to **`--buy-amt`, and the `buy_amt` field inside `--buy-wallets` and `--snip-buy-wallets`**. It does **not** apply to `--sell-configs` (`check_price` there is always a USD market cap, not a token amount). Round to the chain's native decimals. When `--raised-token` is empty/native, no conversion is needed.

## Prerequisites

- `cooking stats`: Only `GMGN_API_KEY` required
- `cooking create`: Both `GMGN_API_KEY` and `GMGN_PRIVATE_KEY` must be configured in `~/.config/gmgn/.env`. The private key must correspond to the wallet bound to the API Key.
- `gmgn-cli` installed globally — if missing, run: `npm install -g gmgn-cli`

**IMPORTANT — Credential lookup order:** `gmgn-cli` loads `~/.config/gmgn/.env` first, then overlays any `.env` found in the **current working directory** (project-level overrides global). If credentials appear missing or wrong, check whether a `.env` in the workspace directory is shadowing the global config:
```bash
ls -la .env 2>/dev/null && echo "WARNING: local .env is overriding ~/.config/gmgn/.env"
```
If a local `.env` exists but lacks `GMGN_API_KEY` / `GMGN_PRIVATE_KEY`, either add them to that file or remove it so the global config is used.

## Rate Limit Handling

All cooking routes go through GMGN's leaky-bucket limiter with `rate=20` and `capacity=20`. Sustained throughput is roughly `20 ÷ weight` requests/second.

| Command | Weight |
|---------|--------|
| `cooking create` | 5 |
| `cooking stats` | 1 |

When a request returns `429`:

- Read `X-RateLimit-Reset` from the response headers — Unix timestamp for when the limit resets.
- If the response body contains `reset_at` (e.g., `{"code":429,"error":"RATE_LIMIT_BANNED","message":"...","reset_at":1775184222}`), extract `reset_at` — it is the Unix timestamp when the ban lifts (typically 5 minutes). Convert to local time and tell the user exactly when they can retry.
- `cooking create` is a real transaction: **never loop or auto-resubmit** after a `429`. Wait until the reset time, then ask for confirmation again before retrying.
- For `RATE_LIMIT_EXCEEDED` or `RATE_LIMIT_BANNED`, repeated requests during cooldown extend the ban by 5 seconds each time, up to 5 minutes.

**First-time setup** (if credentials are not configured):

1. Run the following command — it generates an Ed25519 key pair, saves the private key to `~/.config/gmgn/.env`, and outputs a pre-filled link:
   ```bash
   gmgn-cli config
   ```
2. Click the link output by the command to open the GMGN API Key creation page (Public Key is pre-filled). Create the key and copy the API Key value shown on the page.
3. Write the API Key to `~/.config/gmgn/.env`:
   ```bash
   echo 'GMGN_API_KEY=<key_from_user>' >> ~/.config/gmgn/.env
   ```

### Credential Model

- `GMGN_PRIVATE_KEY` is used exclusively for **local message signing** — the private key never leaves the machine. The CLI computes an Ed25519 signature in-process and transmits only the base64-encoded result in the `X-Signature` request header.
- `GMGN_API_KEY` is transmitted in the `X-APIKEY` header over HTTPS.
- Neither credential is ever passed as a command-line argument.

## `cooking stats` Usage

```bash
gmgn-cli cooking stats [--raw]
```

### `cooking stats` Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `launchpad` | string | Launchpad identifier (e.g. `pump`, `bonk`, `fourmeme`) |
| `token_count` | int | Number of tokens created via GMGN on that launchpad |

## `cooking create` Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--chain` | Yes | Chain: `sol` / `bsc` / `base` |
| `--dex` | Yes | Launchpad platform identifier — see Supported Launchpads table. Never guess this value. |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--name` | Yes | Token full name (e.g. `Doge Killer`) |
| `--symbol` | Yes | Token ticker symbol (e.g. `DOGEK`) |
| `--buy-amt` | Yes | Initial buy amount in **human-readable native token units** (e.g. `0.01` = 0.01 SOL). This is NOT in smallest unit. |
| `--image` | No* | Token logo as **base64-encoded** data (max 2MB decoded). Mutually exclusive with `--image-url`. One of the two is required. |
| `--image-url` | No* | Token logo as a publicly accessible URL. Mutually exclusive with `--image`. One of the two is required. |
| `--slippage` | No* | Slippage tolerance as an integer 0–100, e.g. `30` = 30%. **Mutually exclusive with `--auto-slippage`** — provide one or the other. |
| `--auto-slippage` | No* | Enable automatic slippage. **Mutually exclusive with `--slippage`.** |
| `--description` | No | Token description / project pitch |
| `--website` | No | Project website URL |
| `--twitter` | No | Twitter / X URL |
| `--telegram` | No | Telegram group URL |
| `--fee` | No | Base gas / fee |
| `--priority-fee` | No | Priority fee in SOL (**SOL only**, ≥ 0.0001 SOL) |
| `--tip-fee` | No | Tip fee (SOL ≥ 0.00001 / BSC ≥ 0.000001 BNB; ignored on BASE) |
| `--gas-price` | No | Gas price in wei (EVM chains: BSC / BASE) |
| `--max-fee-per-gas` | No | Max fee per gas in wei (**EVM only**) |
| `--max-priority-fee-per-gas` | No | Max priority fee per gas in wei (**EVM only**) |
| `--anti-mev` | No | Enable anti-MEV protection (**SOL only**; rejected on BSC / BASE) |
| `--anti-mev-mode` | No | Anti-MEV mode: `off` / `normal` / `secure` (**SOL only**) |
| `--raised-token` | No | Raise token symbol. `pump`: `USDC`; `bonk`: `USD1`; `fourmeme`: `USDT` / `USD1`; omit or `""` for native |
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
| `--pump-fee-share-list` | No | Pump.fun fee share list as JSON array: `[{"provider":"twitter","username":"<handle>","basic_points":<n>}]` (**Pump.fun only**) |
| `--flap-rate-conf` | No | Flap rate config as JSON object (**Flap only**) |
| `--fourmeme-rate-conf` | No | FourMeme rate config as JSON object (**FourMeme only**) |
| `--bags-fee-share-list` | No | BAGS fee share list as JSON array: `[{"provider":"twitter","username":"<handle>","basic_points":<n>}]` (**BAGS only**) |
| `--bonk-model` | No | Bonk model identifier (**bonk DEX only**) |
| `--buy-wallets` | No | Multi-wallet buy config as JSON array: `[{"from_address":"<addr>","buy_amt":"<n>"}]` |
| `--snip-buy-wallets` | No | Snipe-buy wallet config as JSON array: `[{"from_address":"<addr>","buy_amt":"<n>"}]` |
| `--buy-trade-config` | No | Buy-side trade config for CondMarket orders as JSON (TradeParam) — see Advanced API Fields |
| `--sell-trade-config` | No | Sell-side trade config for auto-sell / pending_sell as JSON (TradeParam) — see Advanced API Fields |
| `--sell-configs` | No | Auto-sell strategy list as JSON array (CookingSellConfig[]) — see Auto-Sell Configuration |

\* `--image` or `--image-url`: provide exactly one. `--slippage` or `--auto-slippage`: provide exactly one.

## Advanced API Fields

The structured flags (`--pump-fee-share-list`, `--bags-fee-share-list`, `--flap-rate-conf`, `--fourmeme-rate-conf`, `--buy-wallets`, `--snip-buy-wallets`, `--buy-trade-config`, `--sell-trade-config`, `--sell-configs`) each accept a **JSON string**. This section documents the exact JSON schema for each.

### Platform capability matrix

Which advanced features each platform supports. Do not send a field a platform does not support.

| Platform | `--dex` | Chain | Platform-specific fields | Bundle (`--buy-wallets`) | Sniper (`--snip-buy-wallets`) | Cashback | Mayhem |
|---|---|---|---|---|---|---|---|
| Pump.fun | `pump` | SOL | `--pump-fee-share-list` / `--dev-wallet-bps` / `--is-buy-back` | ✅ up to 12 wallets | ✅ up to 10 | ✅ | ✅ |
| Bonk | `bonk` | SOL | `--bonk-model` | ❌ | ✅ up to 10 | ❌ | ❌ |
| BAGS | `bags` | SOL | `--bags-fee-share-list` / `--dev-wallet-bps` | ❌ | ✅ up to 10 | ❌ | ❌ |
| FourMeme | `fourmeme` | BSC | `--fourmeme-rate-conf` | ✅ up to 3 wallets | ✅ up to 10 | ❌ | ❌ |
| Flap | `flap` | BSC | `--flap-rate-conf` | ❌ | ✅ up to 10 | ❌ | ❌ |
| Klik | `klik` | Base | — | ❌ | ✅ up to 10 | ❌ | ❌ |
| Clanker | `clanker` | Base | — | ❌ | ✅ up to 10 | ❌ | ❌ |

- `--is-cashback` / `--is-mayhem` are **Pump.fun only** — other platforms reject them.
- Bundle/auto-sell (`--sell-configs`) and sniper (`--snip-buy-wallets`) are available where the matrix shows ✅.

**Basis-points rule:** any field named `*_bps` / `basic_points` is in basis points (`100` = 1%). Where a section says the shares must sum, all entries must add up to exactly **10000** (FourMeme uses whole percents summing to **100** instead — see below).

**Always talk to the user in percentages, never basis points.** When asking for or confirming any share, fee, or split, phrase it as a percentage (e.g. *"What % goes to this wallet?"* → user says `"50%"`). Convert to the field's unit yourself when building the JSON — never ask the user for a raw bps number:

| User says | `*_bps` field (×100) | FourMeme `*_rate` field (×1) |
|---|---|---|
| `5%` | `500` | `5` |
| `50%` | `5000` | `50` |
| `100%` | `10000` | `100` |

Never set a fee-share split without the user's explicit instruction — it permanently routes token revenue to the listed accounts.

### Pump.fun (`--dex pump`)

> `is_mayhem`, `is_cashback`, `is_buy_back` use their matching CLI flags (`--is-mayhem`, `--is-cashback`, `--is-buy-back`). `pump_fee_share_list` is passed via `--pump-fee-share-list`.

| Field | CLI flag | Description |
|---|---|---|
| `pump_fee_share_list` | `--pump-fee-share-list <json>` | Fee-share list — see JSON schema below |
| `is_buy_back` | `--is-buy-back` | Enable Agent Auto Buyback |

**JSON schema for `--pump-fee-share-list`** — array of objects:

| Field | Type | Required | Description |
|---|---|---|---|
| `provider` | string | Yes | `solana` / `twitter` / `github` |
| `username` | string | Yes | Platform username; a SOL address when `provider` = `solana` |
| `basic_points` | int | Yes | Share in bps — all entries must sum to **10000** |

Example: `--pump-fee-share-list '[{"provider":"twitter","username":"handle","basic_points":10000}]'`

### Bonk (`--dex bonk`)

`dev_wallet_bps` → `--dev-wallet-bps`, `bonk_model` → `--bonk-model`. No additional structured fields.

### BAGS (`--dex bags`)

`dev_wallet_bps` → `--dev-wallet-bps`. `bags_fee_share_list` is passed via `--bags-fee-share-list`.

**JSON schema for `--bags-fee-share-list`** — array of objects:

| Field | Type | Required | Description |
|---|---|---|---|
| `provider` | string | Yes | `twitter` / `solana` / `kick` / `github` |
| `username` | string | Yes | Platform username |
| `basic_points` | int | Yes | Share in bps — combined with `dev_wallet_bps`, all must sum to **10000** |

### Flap (`--dex flap`)

`flap_rate_conf` is passed via `--flap-rate-conf`.

**JSON schema for `--flap-rate-conf`** — single object:

| Field | Type | Required | Description |
|---|---|---|---|
| `beneficiary` | string | Yes | Fee recipient address |
| `tax_rate` | int | Conditional | V5 unified tax rate in bps, e.g. 5% → `500` |
| `buy_tax_rate` | int | Conditional | V6 separate buy tax rate in bps |
| `sell_tax_rate` | int | Conditional | V6 separate sell tax rate in bps |
| `mkt_bps` | int | Yes | Marketing / donation fund share |
| `deflation_bps` | int | Yes | Burn (supply-reduction) share |
| `dividend_bps` | int | Yes | Dividend (holder-reward) share |
| `lp_bps` | int | Yes | Liquidity share |
| `minimum_share_balance` | int | Yes | Min holding to qualify for dividends — minimum **10000** tokens |
| `recipient_type` | string | Yes | `split` (proportional) / `gift` |
| `twitter_account` | string | Yes | Twitter username |
| `split_conf` | array | Yes | Split list — see below |

`split_conf` entries: `{ "recipient": "<address>", "bps": <n> }` — all `bps` must sum to **10000**.

> - Use `tax_rate` for V5 (unified rate); use `buy_tax_rate` + `sell_tax_rate` for V6 (separate rates).
> - When the tax rate > 0: `mkt_bps + deflation_bps + dividend_bps + lp_bps` must sum to **10000**. When `lp_bps > 0`: `minimum_share_balance` must be > 0.

### FourMeme (`--dex fourmeme`)

`fourmeme_rate_conf` is passed via `--fourmeme-rate-conf`.

> `fourmeme_user_login_sign`, `is_approve_allowance`, `is_raised_swap` are broker/jobs **internal** fields — the public API does not accept them, so there is no flag. The multi-quote raise-token retry is handled server-side automatically (poll `order get`); the caller never sets these.

**JSON schema for `--fourmeme-rate-conf`** — single object:

| Field | Type | Required | Description |
|---|---|---|---|
| `fee_plan` | bool | No | Enable the fee plan |
| `recipient_address` | string | Yes | Fee recipient address |
| `fee_rate` | int | Yes | Fee rate, e.g. 5% → `5` (whole percent, not bps) |
| `burn_rate` | int | Yes | Burn share |
| `divide_rate` | int | Yes | Dividend share |
| `liquidity_rate` | int | Yes | Liquidity share |
| `recipient_rate` | int | Yes | Recipient share |
| `min_sharing` | int | Yes | Minimum sharing threshold |

> When `fee_rate > 0`: `burn_rate + divide_rate + liquidity_rate + recipient_rate` must sum to **100**. When `recipient_rate > 0`: `min_sharing` must be > 0.

## Auto-Sell Configuration

`sell_configs` is passed via `--sell-configs` as a JSON array. It schedules conditional sell orders to execute automatically once the token launch succeeds. Omit entirely for a standard launch with no auto-sell.

`--sell-configs` is a JSON array of `CookingSellConfig` objects:

| Field | Type | Required | Description |
|---|---|---|---|
| `sell_type` | string | Yes | `delay_sell` / `limit_order` |
| `delay_sec` | int64 | Conditional | Seconds after buy to trigger; required when `sell_type = delay_sell` |
| `delay_mili_sec` | int64 | No | Milliseconds after buy to trigger; takes precedence over `delay_sec` |
| `sell_ratio` | string | Yes | Fraction to sell — `"1"` = 100%, `"0.5"` = 50% |
| `check_price` | string | Conditional | Market cap in USD to trigger sell; required when `sell_type = limit_order` |
| `wallet_addresses` | []string | Yes | Wallets this strategy applies to (empty array = inert) |

Example: `--sell-configs '[{"sell_type":"delay_sell","delay_sec":60,"sell_ratio":"0.5","wallet_addresses":["<addr>"]}]'`

The buy/sell execution params for these CondMarket orders (slippage, fees, anti-MEV) can be tuned separately via `--buy-trade-config` / `--sell-trade-config` (TradeParam JSON). They do **not** affect the main creation tx, and fall back to the outer-level transaction flags when omitted.

> - **`check_price` is total market cap in USD** — e.g. `"50000"` triggers at a $50,000 market cap.
> - `wallet_addresses` may mix `from_address` and `buy_wallets` entries. The server creates `signal_cooking` for snipe wallets and `pending_sell` for main/bundle wallets automatically.
> - A wallet can carry multiple strategies (e.g. delay-sell 50%, then limit-sell the rest); each applies independently.

### TradeParam (`--buy-trade-config` / `--sell-trade-config`)

These tune the **execution params for the CondMarket buy/sell orders** (bundle buys, sniper buys, and auto-sell). They do **not** affect the main creation transaction (the dev tx uses the outer-level `--dev-*` flags). When omitted, they fall back to the outer-level transaction flags.

`--buy-trade-config` / `--sell-trade-config` each accept a single JSON object:

| Field | Type | Description |
|---|---|---|
| `slippage` | number | Slippage; only sent when truthy |
| `fee` | string | Base gas / fee; only sent when truthy |
| `priority_fee` | string | Priority fee; only sent when truthy |
| `tip_fee` | string | SOL Jito tip; only sent when truthy |
| `gas_price` | string | Gas price in wei (EVM); only sent when truthy |
| `max_priority_fee_per_gas` | string | EVM EIP-1559; only sent when truthy |
| `max_fee_per_gas` | string | EVM EIP-1559; only sent when truthy |
| `auto_slippage` | bool | Always sent |
| `is_anti_mev` | bool | Always sent |
| `anti_mev_mode` | string | `off` / `normal` / `secure`; always sent |

Example: `--buy-trade-config '{"slippage":50,"auto_slippage":false,"priority_fee":"0.0005","tip_fee":"0.0001","is_anti_mev":true,"anti_mev_mode":"secure"}'`

> A standard launch with no `buyConfig` sends `{"is_anti_mev":false,"anti_mev_mode":"off"}` and an empty `buy_wallets` list.

## `cooking create` Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `pending` / `confirmed` / `failed` |
| `hash` | string | Transaction hash (may be empty while `pending`) |
| `order_id` | string | Order ID — pass to `gmgn-cli order get` to poll for final status |
| `error_code` | string | Error code on failure |
| `error_status` | string | Error description on failure |

## Status Polling

Token creation is **asynchronous**. If the initial `cooking create` response shows `status: pending`:

1. Poll with `gmgn-cli order get` every **2 seconds**, up to **30 seconds**:
   ```bash
   gmgn-cli order get --chain <chain> --order-id <order_id>
   ```
2. The new token's contract / mint address is in the **`report.output_token`** field of the `order get` response (only present when `state = 30` and `status = "successful"`) — it is NOT returned by `cooking create` directly.
3. Stop polling once `status` is `confirmed`, `failed`, or `expired`.
4. On `confirmed`: display `output_token` as the token address and include the block explorer link.
5. On `failed` / `expired`: report the `error_status` and do not retry automatically.

## Usage Examples

```bash
# Get token creation statistics per launchpad
gmgn-cli cooking stats

# Create a token on Pump.fun (SOL) — with URL image
gmgn-cli cooking create \
  --chain sol \
  --dex pump \
  --from <wallet_address> \
  --name "My Token" \
  --symbol MAT \
  --buy-amt 0.01 \
  --image-url https://example.com/logo.png \
  --slippage 30 \
  --priority-fee 0.001

# Create a token on FourMeme (BSC) — base64 image + USD1 raise token
gmgn-cli cooking create \
  --chain bsc \
  --dex fourmeme \
  --from <wallet_address> \
  --name "Four Token" \
  --symbol FOUR \
  --buy-amt 0.05 \
  --image "$(base64 -i /path/to/logo.png)" \
  --auto-slippage \
  --raised-token USD1

# Create a token on Bonk (SOL) with anti-MEV
gmgn-cli cooking create \
  --chain sol \
  --dex bonk \
  --from <wallet_address> \
  --name "Bonk Token" \
  --symbol BNKT \
  --buy-amt 0.01 \
  --image-url https://example.com/logo.png \
  --auto-slippage \
  --anti-mev

# Create on Pump.fun with auto-sell: sell 50% 60s after buy
gmgn-cli cooking create \
  --chain sol \
  --dex pump \
  --from <wallet_address> \
  --name "My Token" \
  --symbol MAT \
  --buy-amt 0.01 \
  --image-url https://example.com/logo.png \
  --auto-slippage \
  --sell-configs '[{"sell_type":"delay_sell","delay_sec":60,"sell_ratio":"0.5","wallet_addresses":["<wallet_address>"]}]'
```

### Full worked examples

These mirror real launch configurations end-to-end. Copy and adapt — every JSON flag below is a valid payload shape.

**Pump.fun (SOL) — Bundle + Sniper + Auto-Sell + Agent Auto Buyback**

```bash
gmgn-cli cooking create \
  --chain sol \
  --dex pump \
  --from DevWallet... \
  --name "Demo Coin" \
  --symbol DEMO \
  --buy-amt 0.5 \
  --image-url https://cdn.example.com/coin.png \
  --twitter https://x.com/handle/status/123 \
  --priority-fee 0.0005 \
  --tip-fee 0.0001 \
  --is-buy-back \
  --buy-trade-config '{"slippage":50,"auto_slippage":false,"priority_fee":"0.0005","tip_fee":"0.0001","is_anti_mev":true,"anti_mev_mode":"secure"}' \
  --buy-wallets '[{"from_address":"Wallet1...","buy_amt":"0.1"},{"from_address":"Wallet2...","buy_amt":"0.1"}]' \
  --snip-buy-wallets '[{"from_address":"Sniper1...","buy_amt":"0.05"}]' \
  --sell-configs '[{"sell_type":"delay_sell","sell_ratio":"1","wallet_addresses":["Wallet1..."],"delay_mili_sec":5000}]'
```

- `--is-buy-back` is the Agent Auto Buyback mode (the backend also sets the agent fee internally).
- `buy_amt` values in `--buy-wallets` / `--snip-buy-wallets` are in native SOL.
- Bundle wallets ≤ 12, sniper wallets ≤ 10 on Pump.fun (see capability matrix).

**FourMeme (BSC) — user fee split + raise token USDT**

```bash
gmgn-cli cooking create \
  --chain bsc \
  --dex fourmeme \
  --from 0xDev... \
  --name "Demo BSC" \
  --symbol DBSC \
  --buy-amt 0.0123 \
  --image-url https://cdn.example.com/coin.png \
  --raised-token USDT \
  --website https://demo.com \
  --gas-price 1000000000 \
  --auto-slippage \
  --fourmeme-rate-conf '{"fee_rate":1,"recipient_rate":50,"burn_rate":20,"divide_rate":20,"liquidity_rate":10,"min_sharing":100000,"recipient_address":"0xDev..."}'
```

- `--buy-amt 0.0123` is **already converted to native BNB** from the USDT amount the user wanted (see Quote Token conversion). Do the conversion before building the command.
- `--gas-price 1000000000` is wei (1 Gwei).
- In `--fourmeme-rate-conf`, `recipient_rate + burn_rate + divide_rate + liquidity_rate` must sum to **100**.

## Output Format

### Pre-create Confirmation

Before every `cooking create`, present this summary and wait for explicit user confirmation:

```
⚠️ Token Creation Confirmation Required

Chain:        {chain}
Platform:     {--dex} (e.g. pump / fourmeme)
Wallet:       {--from}
Token Name:   {--name}
Symbol:       {--symbol}
Initial Buy:  {--buy-amt} {native currency} (e.g. 0.01 SOL)
Slippage:     {--slippage}% (or "auto")
Image:        {--image-url or "base64 provided"}
Social:       {twitter / telegram / website if provided}
Modes:        {Mayhem / Cashback / Agent Auto Buyback if set, else "none"}
Fee Share:    {recipient → % list if set, else "none"}
Auto-Sell:    {sell_configs summary if set, else "none"}

Reply "confirm" to deploy this token. This action is IRREVERSIBLE.
```

Omit the Modes / Fee Share / Auto-Sell lines if none were configured — or show them as `none` — but if any **are** set, they MUST appear here so the user re-confirms them explicitly.

### Post-create Receipt

After polling confirms a successful deployment:

```
✅ Token Created

Token:    {--name} ({--symbol})
Address:  {report.output_token from order get}
Chain:    {chain}
Platform: {--dex}
Tx:       {explorer link for hash}
Order ID: {order_id}
```

Block explorer links:

| Chain | Explorer |
|-------|----------|
| sol   | `https://solscan.io/tx/<hash>` |
| bsc   | `https://bscscan.com/tx/<hash>` |
| base  | `https://basescan.org/tx/<hash>` |

## Guided Launch Flow

When a user says they want to launch / create / deploy a token but has not provided all required information, collect information **one required field at a time** — never bundle multiple required fields into a single question. The user should be able to reply with a single value, not a labeled list.

Ask each required field as a short, direct question. Wait for the answer before moving to the next. Optional fields are grouped into one question after all required fields are collected.

### Step 1 — Chain & Platform

Ask: *"Which chain and platform?"*

Show the options concisely:

| Chain  | Platform   | `--dex`    |
| ------ | ---------- | ---------- |
| Solana | Pump.fun   | `pump`     |
| Solana | Bonk       | `bonk`     |
| Solana | BAGS       | `bags`     |
| BSC    | FourMeme   | `fourmeme` |
| BSC    | Flap       | `flap`     |
| Base   | Klik       | `klik`     |
| Base   | Clanker    | `clanker`  |

If the user is unsure, recommend: **Pump.fun (SOL)** or **FourMeme (BSC)**.

The chosen platform determines which advanced options are available later in Step 7 (e.g. Mayhem/Cashback/Agent Auto Buyback on Pump.fun, fee-share splits on BAGS/Flap/FourMeme). Note the platform now; do not ask about advanced options yet.

### Step 2 — Token Name

Ask: *"Token name?"*

Wait for the user's reply (e.g. `Doge Killer`).

### Step 3 — Token Symbol

Ask: *"Ticker symbol?"*

Wait for the user's reply (e.g. `DOGEK`). Typically 3–8 uppercase characters.

### Step 4 — Logo

Ask: *"Logo image? (file path or URL — skip to launch without one)"*

- **File path** → silently run `base64 -i <path>` and pass the result to `--image`. Do not mention "base64" to the user.
- **URL** → use `--image-url` directly.
- **Skip / none** → proceed without a logo. Note that most platforms accept this, but it reduces visibility.

### Step 5 — Initial Buy Amount

Ask: *"How much {SOL / BNB / ETH} for the initial buy?"*

Pass the user's answer directly to `--buy-amt` — already in full token units (e.g. `0.01` = 0.01 SOL). Do NOT convert to lamports or wei.

### Step 6 — Optional Details (single question)

Ask all optional fields together in one message:

*"Any optional extras? (skip any you don't need)"*
- *Description* — one-line pitch shown on the launchpad
- *Twitter* — Twitter / X URL
- *Telegram* — Telegram group URL
- *Website* — project website URL

The user can reply with just the ones they have, or say "skip" / "none" to proceed.

### Step 7 — Platform Modes, Fees & Auto-Sell (platform-dependent)

After the basics are collected, ask **once** whether the user wants any advanced options for the platform they chose. Default everyone to a plain fair launch — only configure these when the user explicitly asks. Tailor the question to the selected platform; do not list options that don't apply to it.

Ask: *"Want any advanced options, or launch with defaults? (reply 'defaults' to skip)"* — then offer the relevant subset.

**Phrase the question around the platform the user picked — only ask about modes that exist on that platform.** For example, on **Pump.fun** ask specifically:
- *"Enable Cashback mode?"* (`--is-cashback`)
- *"Enable Agent Auto Buyback mode?"* (`--is-buy-back`)
- *"Enable Mayhem mode?"* (`--is-mayhem`)
- *"Set up a fee-share split?"* (`--pump-fee-share-list`)
- *"Want me to remember these advanced settings for your next launch?"* — if yes, save them to memory so future launches can pre-fill the same choices.

Bonk / BAGS / Flap / FourMeme have **no mode toggles** — for those, skip the mode questions and only ask about fee-share split and auto-sell.

The relevant options per platform:

- **Pump.fun modes** — Mayhem (`--is-mayhem`), Cashback (`--is-cashback`), Agent Auto Buyback (`--is-buy-back`).
- **Fee-share split** — Pump.fun (`--pump-fee-share-list`), BAGS (`--dev-wallet-bps` + `--bags-fee-share-list`), Bonk (`--dev-wallet-bps`), Flap (`--flap-rate-conf`), FourMeme (`--fourmeme-rate-conf`). See [Advanced API Fields](#advanced-api-fields) for JSON schemas. **Warn the user this permanently routes token revenue to the listed accounts.** Always ask the user for shares as percentages — convert to bps yourself. Shares must add up to 100%.
- **Auto-sell** — `--sell-configs` (JSON): delay-sell (sell a fraction N seconds after the buy) and/or limit-sell (sell once market cap hits a USD target). See [Auto-Sell Configuration](#auto-sell-configuration). Confirm the sell ratio and trigger before setting it.

If the user says "defaults" / "skip" / "none", proceed with none of these set.

### Step 8 — Confirmation & Execute

Once all information is collected, present the pre-create confirmation summary (see Output Format section) and wait for the user to reply "confirm" before executing. If any advanced options from Step 7 were set, they MUST appear in the summary so the user re-confirms them explicitly.

---

## Execution Guidelines

- **[REQUIRED] Pre-create confirmation** — Before executing `cooking create`, present the full summary above and receive explicit "confirm" from the user. No exceptions. Do NOT auto-create.
- **[REQUIRED] `--dex` validation** — Before running, look up the user's named platform in the Supported Launchpads table and resolve to the correct `--dex` identifier. Never guess or pass a freeform platform name. If the chain/platform combination is not in the table, tell the user it is unsupported.
- **Slippage requirement** — Either `--slippage` or `--auto-slippage` must be provided. If the user did not specify, suggest `--auto-slippage` for volatile new tokens or ask for a preference.
- **Image handling** — If the user provides a file path, run `base64 -i <path>` and pass the result to `--image`. If they provide a URL, use `--image-url`. If neither is provided, ask before building the confirmation — most platforms require a logo.
- **Fee-share / bps inputs** — Always collect and confirm shares as percentages with the user; convert to basis points yourself (50% → `5000`). Never ask for a raw bps value.
- **Address validation** — Validate `--from` wallet address format before submitting:
  - `sol`: base58, 32–44 characters
  - `bsc` / `base`: `0x` + 40 hex digits
- **Chain-wallet compatibility** — SOL addresses are incompatible with EVM chains and vice versa. Warn the user and abort if the address format does not match the chain.
- **Order polling** — After `cooking create`, if `status` is `pending`, poll `order get` every 2 seconds up to 30 seconds. The token address is in `report.output_token`. Do not report success until `status` is `confirmed`.
- **Credential sensitivity** — `GMGN_API_KEY` and `GMGN_PRIVATE_KEY` can execute real transactions. Never log, display, or expose these values.

## Notes

- `cooking create` uses **signed auth** (API Key + signature) — CLI handles signing automatically.
- `cooking stats` uses exist auth (API Key only — no private key needed).
- The new token's mint address is in `report.output_token` from `gmgn-cli order get`, not in the initial `cooking create` response.
- Use `--raw` on any command to get single-line JSON for further processing.

## References

| Skill | Description |
|-------|-------------|
| [gmgn-swap](https://github.com/GMGNAI/gmgn-skills/tree/main/skills/gmgn-swap) | Contains `order get` command used for polling token creation status |
| [gmgn-token](https://github.com/GMGNAI/gmgn-skills/tree/main/skills/gmgn-token) | Token security check, info, holders, and traders — useful after launch to monitor your token |
| [gmgn-market](https://github.com/GMGNAI/gmgn-skills/tree/main/skills/gmgn-market) | `market trenches` for tracking bonding curve progress; `market trending` to see if your token is gaining traction |
| [gmgn-track](https://github.com/GMGNAI/gmgn-skills/tree/main/skills/gmgn-track) | Smart money and KOL trade tracking — monitor whether smart wallets are buying your token after launch |
| [gmgn-portfolio](https://github.com/GMGNAI/gmgn-skills/tree/main/skills/gmgn-portfolio) | Wallet holdings and P&L — check your own wallet balance before deciding on `--buy-amt` |
