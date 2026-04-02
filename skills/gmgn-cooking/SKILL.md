---
name: gmgn-cooking
description: "[FINANCIAL EXECUTION] Create tokens on launchpad platforms (Pump.fun, Raydium, PancakeSwap, Flap, FourMeme, Bonk, BAGS, etc.) or query token creation statistics by launchpad. Token creation executes irreversible on-chain transactions. Requires explicit user confirmation before every create. Supports sol / bsc / base."
argument-hint: "stats | [create --chain <chain> --dex <dex> --from <addr> --name <name> --symbol <sym> --buy-amt <n> (--image <base64> | --image-url <url>)]"
metadata:
  cliHelp: "gmgn-cli cooking --help"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai.**

**⚠️ Token creation executes REAL, IRREVERSIBLE blockchain transactions. Always require explicit user confirmation before running `cooking create`.**

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `cooking stats` | Get token creation statistics grouped by launchpad (normal auth) |
| `cooking create` | Create a token on a launchpad platform (requires private key) |

## Supported Chains

`sol` / `bsc` / `base` / `eth` / `ton`

## Supported Launchpads by Chain

| Chain | Supported DEX / Launchpad |
|-------|--------------------------|
| `sol` | `pump` / `raydium` / `bonk` / `bags` / `memoo` / `letsbonk` / `bonkers` |
| `bsc` | `pancakeswap` / `flap` / `fourmeme` |
| `base` | `clanker` / `flaunch` / `baseapp` / `basememe` / `zora` / `virtuals_v2` |

## Prerequisites

- `cooking stats`: Only `GMGN_API_KEY` required
- `cooking create`: Both `GMGN_API_KEY` and `GMGN_PRIVATE_KEY` must be configured in `~/.config/gmgn/.env`. The private key must correspond to the wallet bound to the API Key.
- `gmgn-cli` installed globally — if missing, run: `npm install -g gmgn-cli`

## `cooking stats` Usage

```bash
gmgn-cli cooking stats [--raw]
```

**Response fields (data array):**

| Field | Type | Description |
|-------|------|-------------|
| `launchpad` | string | Launchpad identifier (e.g. `pump`, `raydium`, `pancakeswap`) |
| `token_count` | int | Number of tokens created on that launchpad |

## `cooking create` Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--chain` | Yes | Chain: `sol` / `bsc` / `base` / `eth` / `ton` |
| `--dex` | Yes | Launchpad platform (see Supported Launchpads table) |
| `--from` | Yes | Wallet address (must match API Key binding) |
| `--name` | Yes | Token name |
| `--symbol` | Yes | Token symbol |
| `--buy-amt` | Yes | Initial buy amount in native token (e.g. `0.01` for 0.01 SOL) |
| `--image` | No* | Token logo as base64-encoded data (max 2MB decoded). One of `--image` or `--image-url` is required |
| `--image-url` | No* | Token logo URL. One of `--image` or `--image-url` is required |
| `--website` | No | Website URL |
| `--twitter` | No | Twitter link |
| `--telegram` | No | Telegram link |
| `--slippage` | No | Slippage tolerance, e.g. `0.01` = 1%. Mutually exclusive with `--auto-slippage` |
| `--auto-slippage` | No | Enable automatic slippage |
| `--priority-fee` | No | Priority fee in SOL (SOL only, ≥ 0.0001 SOL) |
| `--tip-fee` | No | Tip fee (SOL ≥ 0.00001 / BSC ≥ 0.000001 BNB; ignored on ETH/BASE) |
| `--gas-price` | No | Gas price in wei (EVM chains) |
| `--anti-mev` | No | Enable anti-MEV protection |

## `cooking create` Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `pending` / `confirmed` / `failed` |
| `hash` | string | Transaction hash (may be empty while pending) |
| `order_id` | string | Order ID for polling via `order get` |
| `error_code` | string | Error code on failure |
| `error_status` | string | Error description on failure |

Token creation is asynchronous. If `status` is `pending`, poll with `gmgn-cli order get --chain <chain> --order-id <order_id>` every 2 seconds (up to 30 seconds). The new token's mint address is available in the order detail's `output_token` field once confirmed.

## Usage Examples

```bash
# Get launchpad creation statistics
gmgn-cli cooking stats

# Create a token on Pump.fun (SOL)
gmgn-cli cooking create \
  --chain sol \
  --dex pump \
  --from <wallet_address> \
  --name "My Token" \
  --symbol MAT \
  --buy-amt 0.01 \
  --image-url https://example.com/logo.png \
  --slippage 0.01 \
  --priority-fee 0.001

# Create a token on PancakeSwap (BSC)
gmgn-cli cooking create \
  --chain bsc \
  --dex pancakeswap \
  --from <wallet_address> \
  --name "BSC Token" \
  --symbol BSCT \
  --buy-amt 0.01 \
  --image-url https://example.com/logo.png \
  --slippage 0.02 \
  --gas-price 5000000000 \
  --website https://mytoken.io \
  --twitter https://twitter.com/mytoken
```

## Notes

- `cooking create` uses **critical auth** (API Key + signature) — CLI handles signing automatically
- Either `--image` (base64) or `--image-url` is required; both `--slippage` and `--auto-slippage` cannot be omitted (provide one)
- After creation, poll `order get` to get `confirmed` status and the new token's mint address from `output_token`
- Use `--raw` to get single-line JSON for further processing
