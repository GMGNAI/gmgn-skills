---
name: gmgn-portfolio
description: Query GMGN wallet portfolio — API Key wallet info, holdings, transaction activity, trading stats, and token balance. Supports sol / bsc / base.
argument-hint: "<info|holdings|activity|stats|token-balance> [--chain <sol|bsc|base>] [--wallet <wallet_address>]"
metadata:
  cliHelp: "gmgn-cli portfolio --help"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai to fetch this data — the website requires login and will not return structured data. The CLI is the only correct method.**

**⚠️ IPv6 NOT SUPPORTED: If you get a `401` or `403` error and credentials look correct, check for IPv6 immediately: (1) list all network interfaces and their IPv6 addresses — run `ifconfig | grep inet6` (macOS) or `ip addr show | grep inet6` (Linux); (2) send a test request to `https://ipv6.icanhazip.com` — if the response is an IPv6 address, outbound traffic is going via IPv6. Tell the user immediately: "Please disable IPv6 on your network interface — gmgn-cli commands only work over IPv4."**

Use the `gmgn-cli` tool to query wallet portfolio data based on the user's request.

**For full wallet analysis (holdings + stats + activity + verdict), follow [`docs/workflow-wallet-analysis.md`](../../docs/workflow-wallet-analysis.md)**

## Core Concepts

- **`realized_profit` vs `unrealized_profit`** — `realized_profit` = profit locked in from completed sells (cash in hand). `unrealized_profit` = paper gains on positions still held, calculated at current price. These are separate numbers — do not add them unless answering "total P&L including open positions."

- **`profit_change`** — A multiplier ratio, not a dollar amount. `1.5` = +150% return. `0` = break-even. `-0.5` = -50% loss. Computed as `total_profit / cost`. Do not display this as a raw decimal — convert to percentage for user-facing output.

- **`pnl`** — Profit/loss ratio from `portfolio stats`: `realized_profit / total_cost`. Same multiplier format as `profit_change`. A `pnl` of `2.0` means the wallet doubled its money on completed trades over the period.

- **`winrate`** — Ratio of profitable trades over the period (0–1). `0.6` = 60% of trades were profitable. Does not reflect the size of wins vs losses — a wallet can have high winrate but net negative if losses are large.

- **`cost` vs `usd_value`** — In holdings: `cost` is the historical amount spent buying this token (your cost basis); `usd_value` is the current market value of the position. The difference is unrealized P&L.

- **`history_bought_cost` vs `cost`** — `history_bought_cost` is the all-time cumulative spend on this token (including positions already sold). `cost` is the cost basis of the current open position only.

- **Pagination (`cursor`)** — Activity results are paginated. The response includes a `next` field; pass it as `--cursor` to fetch the next page. An empty or missing `next` means you are on the last page.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `portfolio info` | Wallets and main currency balances bound to the API Key |
| `portfolio holdings` | Wallet token holdings with P&L |
| `portfolio activity` | Transaction history |
| `portfolio stats` | Trading statistics (supports batch) |
| `portfolio token-balance` | Token balance for a specific token |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `gmgn-cli` installed globally — if missing, run: `npm install -g gmgn-cli`
- `GMGN_API_KEY` configured in `~/.config/gmgn/.env`

## Rate Limit Handling

All portfolio routes used by this skill go through GMGN's leaky-bucket limiter with `rate=10` and `capacity=10`. Sustained throughput is roughly `10 ÷ weight` requests/second, and the max burst is roughly `floor(10 ÷ weight)` when the bucket is full.

| Command | Route | Weight |
|---------|-------|--------|
| `portfolio info` | `GET /v1/user/info` | 1 |
| `portfolio holdings` | `GET /v1/user/wallet_holdings` | 2 |
| `portfolio activity` | `GET /v1/user/wallet_activity` | 3 |
| `portfolio stats` | `GET /v1/user/wallet_stats` | 3 |
| `portfolio token-balance` | `GET /v1/user/wallet_token_balance` | 1 |

When a request returns `429`:

- Read `X-RateLimit-Reset` from the response headers. It is a Unix timestamp in seconds that marks when the limit is expected to reset.
- If the response body contains `reset_at` (e.g., `{"code":429,"error":"RATE_LIMIT_BANNED","message":"...","reset_at":1775184222}`), extract `reset_at` — it is the Unix timestamp when the ban lifts (typically 5 minutes). Convert to local time and tell the user exactly when they can retry.
- The CLI may wait and retry once automatically when the remaining cooldown is short. If it still fails, stop and tell the user the exact retry time instead of sending more requests.
- For `RATE_LIMIT_EXCEEDED` or `RATE_LIMIT_BANNED`, repeated requests during the cooldown can extend the ban by 5 seconds each time, up to 5 minutes. Do not spam retries.

**First-time setup** (if `GMGN_API_KEY` is not configured):

1. Generate key pair and show the public key to the user:
   ```bash
   openssl genpkey -algorithm ed25519 -out /tmp/gmgn_private.pem 2>/dev/null && \
     openssl pkey -in /tmp/gmgn_private.pem -pubout 2>/dev/null
   ```
   Tell the user: *"This is your Ed25519 public key. Go to **https://gmgn.ai/ai**, paste it into the API key creation form, then send me the API Key value shown on the page."*

2. Wait for the user's API key, then configure:
   ```bash
   mkdir -p ~/.config/gmgn
   echo 'GMGN_API_KEY=<key_from_user>' > ~/.config/gmgn/.env
   chmod 600 ~/.config/gmgn/.env
   ```

## Usage Examples

```bash
# API Key wallet info (no --chain or --wallet needed)
gmgn-cli portfolio info

# Wallet holdings (default sort)
gmgn-cli portfolio holdings --chain sol --wallet <wallet_address>

# Holdings sorted by USD value, descending
gmgn-cli portfolio holdings \
  --chain sol --wallet <wallet_address> \
  --order-by usd_value --direction desc --limit 20

# Include sold-out positions
gmgn-cli portfolio holdings --chain sol --wallet <wallet_address> --sell-out

# Transaction activity
gmgn-cli portfolio activity --chain sol --wallet <wallet_address>

# Activity filtered by type
gmgn-cli portfolio activity --chain sol --wallet <wallet_address> \
  --type buy --type sell

# Activity for a specific token
gmgn-cli portfolio activity --chain sol --wallet <wallet_address> \
  --token <token_address>

# Trading stats (default 7d)
gmgn-cli portfolio stats --chain sol --wallet <wallet_address>

# Trading stats for 30 days
gmgn-cli portfolio stats --chain sol --wallet <wallet_address> --period 30d

# Batch stats for multiple wallets
gmgn-cli portfolio stats --chain sol \
  --wallet <wallet_1> --wallet <wallet_2>

# Token balance
gmgn-cli portfolio token-balance \
  --chain sol --wallet <wallet_address> --token <token_address>
```

## `portfolio holdings` Options

| Option | Description |
|--------|-------------|
| `--limit <n>` | Page size (default `20`, max 50) |
| `--cursor <cursor>` | Pagination cursor |
| `--order-by <field>` | Sort field: `usd_value` / `last_active_timestamp` / `realized_profit` / `unrealized_profit` / `total_profit` / `history_bought_cost` / `history_sold_income` (default `usd_value`) |
| `--direction <asc\|desc>` | Sort direction (default `desc`) |
| `--hide-abnormal <bool>` | Hide abnormal positions: `true` / `false` (default: `false`) |
| `--hide-airdrop <bool>` | Hide airdrop positions: `true` / `false` (default: `true`) |
| `--hide-closed <bool>` | Hide closed positions: `true` / `false` (default: `true`) |
| `--hide-open` | Hide open positions |

## `portfolio activity` Options

| Option | Description |
|--------|-------------|
| `--token <address>` | Filter by token |
| `--limit <n>` | Page size |
| `--cursor <cursor>` | Pagination cursor (pass the `next` value from the previous response) |
| `--type <type>` | Repeatable: `buy` / `sell` / `add` / `remove` / `transfer` |

The activity response includes a `next` field. Pass it to `--cursor` to fetch the next page.

## `portfolio stats` Options

| Option | Description |
|--------|-------------|
| `--period <period>` | Stats period: `7d` / `30d` (default `7d`) |

## Response Field Reference

### `portfolio holdings` — Key Fields

The response has a `holdings` array. Each item is one token position.

| Field | Description |
|-------|-------------|
| `token.address` | Token contract address |
| `token.symbol` / `token.name` | Token ticker and full name |
| `token.price` | Current token price in USD |
| `balance` | Current token balance (human-readable units) |
| `usd_value` | Current USD value of this position |
| `cost` | Total amount spent buying this token (USD) |
| `realized_profit` | Profit from completed sells (USD) |
| `unrealized_profit` | Profit on current unsold holdings at current price (USD) |
| `total_profit` | `realized_profit + unrealized_profit` (USD) |
| `profit_change` | Total profit ratio = `total_profit / cost` (e.g. `1.5` = +150%) |
| `avg_cost` | Average buy price per token (USD) |
| `buy_tx_count` | Number of buy transactions |
| `sell_tx_count` | Number of sell transactions |
| `last_active_timestamp` | Unix timestamp of the most recent transaction |
| `history_bought_cost` | Total USD spent buying (all-time) |
| `history_sold_income` | Total USD received from selling (all-time) |

### `portfolio activity` — Key Fields

The response has a `activities` array and a `next` cursor field for pagination.

| Field | Description |
|-------|-------------|
| `transaction_hash` | On-chain transaction hash |
| `type` | Transaction type: `buy` / `sell` / `add` / `remove` / `transfer` |
| `token.address` | Token contract address |
| `token.symbol` | Token ticker |
| `token_amount` | Token quantity in this transaction |
| `cost_usd` | USD value of this transaction |
| `price` | Token price in USD at time of transaction |
| `timestamp` | Unix timestamp of the transaction |
| `next` | Pagination cursor — pass to `--cursor` to fetch the next page |

### `portfolio stats` — Key Fields

The response is an object (or array for batch). Key fields:

| Field | Description |
|-------|-------------|
| `realized_profit` | Total realized profit over the period (USD) |
| `unrealized_profit` | Total unrealized profit on open positions (USD) |
| `winrate` | Win rate — ratio of profitable trades (0–1) |
| `total_cost` | Total amount spent buying in the period (USD) |
| `buy_count` | Number of buy transactions |
| `sell_count` | Number of sell transactions |
| `pnl` | Profit/loss ratio = `realized_profit / total_cost` |

The response also includes a `common` object when available (absent if the upstream identity service is unavailable):

| Field | Description |
|-------|-------------|
| `common.avatar` | Wallet avatar URL |
| `common.name` | Display name |
| `common.ens` | ENS domain (EVM chains only) |
| `common.tag` | Primary wallet tag |
| `common.tags` | All wallet tags (e.g. `["smart_money"]`) |
| `common.twitter_username` | Twitter handle |
| `common.twitter_name` | Twitter display name |
| `common.followers_count` | Twitter follower count |
| `common.is_blue_verified` | Twitter blue-verified badge |
| `common.follow_count` | Number of GMGN users following this wallet |
| `common.remark_count` | Number of GMGN users who have remarked this wallet |
| `common.created_token_count` | Tokens created by this wallet |
| `common.created_at` | Wallet creation time (Unix seconds) — records when the first funding transaction arrived; use this as the wallet's age indicator |
| `common.fund_from` | Funding source label |
| `common.fund_from_address` | Address that funded this wallet |
| `common.fund_amount` | Funding amount |

Use `common.tags` and `common.twitter_username` when building a wallet profile narrative. If `common` is absent in the response, omit identity fields silently — do not report it as an error.

**Do NOT guess field names not listed here.** If a field appears in the response but is not in this table, do not interpret it without reading the raw output first.

## Output Format

**Do NOT dump raw JSON.** Always parse and present data in the structured formats below. Use `--raw` only when piping to `jq` or further processing.

### `portfolio holdings` — Holdings Table

Present a table sorted by `usd_value` (descending). Show total portfolio value at the top.

```
Wallet: {wallet} | Chain: {chain}
Total value: ~${sum of usd_value across all positions}

# | Token | Balance | USD Value | Total P&L | P&L% | Avg Cost | Buys / Sells
```

Flag positions where `profit_change` is strongly negative (e.g. < -50%) or positive (e.g. > 200%) with a brief note.

### `portfolio activity` — Activity Feed

Present as a chronological list (newest first). Use human-readable timestamps.

```
{type} {token.symbol}  |  {token_amount} tokens  |  ${cost_usd}  |  {timestamp}  |  tx: {short hash}
```

Group by token if the user asks about a specific token.

### `portfolio stats` — Stats Summary

```
Wallet: {wallet} | Period: {period}
Realized P&L:   ${realized_profit}
Unrealized P&L: ${unrealized_profit}
Win Rate:        {winrate × 100}%
Total Spent:     ${total_cost}
Buys / Sells:    {buy_count} / {sell_count}
PnL Ratio:       {pnl}x
[Identity:       {common.name or common.twitter_username} | Tags: {common.tags}]
```

Show the `[Identity: ...]` line only if `common` is present in the response. For batch queries (multiple wallets), present one summary block per wallet.

## Notes

- All portfolio commands use normal auth (API Key only, no signature required)
- `portfolio stats` supports multiple `--wallet` flags for batch queries
- Use `--raw` to get single-line JSON for further processing
- **Input validation** — Wallet and token addresses are validated against the expected chain format at runtime (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits). The CLI exits with an error on invalid input.
- For follow-wallet, KOL, and Smart Money trade records, use the `gmgn-track` skill (`track follow-wallet` / `track kol` / `track smartmoney`)

## Workflow

For full wallet analysis including trade history and follow-through on top holdings, see [`docs/workflow-wallet-analysis.md`](../../docs/workflow-wallet-analysis.md)

For in-depth trading style analysis, copy-trade ROI estimation, and smart money leaderboard comparison, see [`docs/workflow-smart-money-profile.md`](../../docs/workflow-smart-money-profile.md)

**When to use which:**
- User asks "is this wallet worth following" → [`docs/workflow-wallet-analysis.md`](../../docs/workflow-wallet-analysis.md)
- User asks "what's this wallet's trading style", "when does he take profit", "smart money profile", "if I copied this wallet what would my return be" → [`docs/workflow-smart-money-profile.md`](../../docs/workflow-smart-money-profile.md)
- User wants to compare multiple smart money wallets by winrate/PnL → [`docs/workflow-smart-money-profile.md`](../../docs/workflow-smart-money-profile.md) Step 5 (leaderboard)
