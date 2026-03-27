---
name: gmgn-track
description: Query GMGN on-chain tracking data — follow-wallet trade records, KOL trades, and Smart Money trades. Supports sol / bsc / base.
argument-hint: "<follow-wallet|kol|smartmoney> [--chain <sol|bsc|base>] [--wallet <wallet_address>]"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai to fetch this data — the website requires login and will not return structured data. The CLI is the only correct method.**

**⚠️ IPv6 NOT SUPPORTED: GMGN CLI commands do not support IPv6. If you get a `401` or `403` error and credentials look correct, the outbound connection is likely going via IPv6. Run `curl -s https://api64.ipify.org` to check — if the result is an IPv6 address, tell the user to ensure their network routes requests over IPv4.**

## ⚠️ IPv6 Not Supported — CRITICAL

**The `track follow-wallet` sub-command does NOT support IPv6. Requests MUST go out over IPv4.**

This sub-command is known to fail with `401` or `403` when the outbound connection uses IPv6 — even when credentials are valid.

**How to diagnose:**
```bash
curl -s https://api64.ipify.org   # if result is an IPv6 address, that's the problem
```

**Rule for AI models:** If `track follow-wallet` returns 401/403 and credentials look correct — stop and tell the user: "Your outbound connection may be using IPv6, which is not supported by this command. Please check your network configuration and ensure requests go out over IPv4."

Use the `gmgn-cli` tool to query on-chain tracking data based on the user's request.

**When to use which sub-command:**
- `track follow-wallet` — user asks "what did the wallets I follow trade?", "show me my follow list trades", "追踪关注的钱包交易动态" → requires wallets followed via GMGN platform
- `track kol` — user asks "what are KOLs buying?", "KOL 最近在买什么", "show me influencer trades" → returns trades from known KOL wallets
- `track smartmoney` — user asks "what is smart money doing?", "聪明钱最近在买什么", "show me whale trades" → returns trades from smart money / whale wallets

**Do NOT confuse these three:**
- `follow-wallet` = wallets the user has personally followed on GMGN
- `kol` = platform-tagged KOL / influencer wallets (not user-specific)
- `smartmoney` = platform-tagged smart money / whale wallets (not user-specific)

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `track follow-wallet` | Trade records from wallets the user personally follows on GMGN |
| `track kol` | Real-time trades from KOL / influencer wallets tagged by GMGN |
| `track smartmoney` | Real-time trades from smart money / whale wallets tagged by GMGN |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `.env` file with `GMGN_API_KEY` set
- `GMGN_PRIVATE_KEY` required for `track follow-wallet` (signature auth); not needed for `track kol` / `track smartmoney`
- Run from the directory where your `.env` file is located, or set `GMGN_HOST` in your environment
- `gmgn-cli` installed globally: `npm install -g gmgn-cli`

## Usage Examples

```bash
# Follow-wallet trades (all wallets you follow)
gmgn-cli track follow-wallet --chain sol

# Follow-wallet trades filtered by wallet
gmgn-cli track follow-wallet --chain sol --wallet <wallet_address>

# Follow-wallet filtered by trade direction
gmgn-cli track follow-wallet --chain sol --side buy

# Follow-wallet filtered by USD amount range
gmgn-cli track follow-wallet --chain sol --min-amount-usd 100 --max-amount-usd 10000

# KOL trade records (SOL, default)
gmgn-cli track kol --limit 10 --raw

# KOL trade records on SOL, buy only
gmgn-cli track kol --chain sol --side buy --limit 10 --raw

# Smart Money trade records (SOL, default)
gmgn-cli track smartmoney --limit 10 --raw

# Smart Money trade records, sell only
gmgn-cli track smartmoney --chain sol --side sell --limit 10 --raw
```

## `track follow-wallet` Options

| Option | Description |
|--------|-------------|
| `--chain` | Required. `sol` / `bsc` / `base` |
| `--wallet <address>` | Filter by wallet address |
| `--limit <n>` | Page size (1–100, default 10) |
| `--side <side>` | Trade direction: `buy` / `sell` |
| `--filter <tag...>` | Repeatable filter conditions |
| `--min-amount-usd <n>` | Minimum trade amount (USD) |
| `--max-amount-usd <n>` | Maximum trade amount (USD) |

## `track kol` / `track smartmoney` Options

| Option | Description |
|--------|-------------|
| `--chain <chain>` | Chain: `sol` / `bsc` / `base` (default `sol`) |
| `--limit <n>` | Page size (1–200, default 100) |
| `--side <side>` | Filter by trade direction: `buy` / `sell` (client-side filter — applied locally after fetching results) |

## `track follow-wallet` Response Fields

Top-level fields:

| Field | Description |
|-------|-------------|
| `next_page_token` | Opaque token for fetching the next page of results |
| `list` | Array of trade records |

Each item in `list` contains:

| Field | Description |
|-------|-------------|
| `id` | Record ID (base64-encoded, use as cursor) |
| `chain` | Chain name (e.g. `sol`) |
| `transaction_hash` | On-chain transaction hash |
| `maker` | Wallet address of the followed wallet |
| `side` | Trade direction: `buy` or `sell` |
| `base_address` | Token contract address |
| `quote_address` | Quote token address (SOL native address for buys/sells on SOL) |
| `base_amount` | Token quantity in smallest unit |
| `quote_amount` | Quote token amount spent / received (e.g. SOL) |
| `amount_usd` | Trade value in USD |
| `cost_usd` | Same as `amount_usd` — USD value of this transaction leg |
| `buy_cost_usd` | Original buy cost in USD (`0` if this record is the buy itself) |
| `price` | Token price denominated in quote token at time of trade |
| `price_usd` | Token price in USD at time of trade |
| `price_now` | Token current price in USD |
| `price_change` | Price change ratio since trade time (e.g. `6.66` = +666%) |
| `timestamp` | Unix timestamp of the trade |
| `is_open_or_close` | `1` = full position open or close; `0` = partial add or reduce |
| `launchpad` | Launchpad display name (e.g. `Pump.fun`) |
| `launchpad_platform` | Launchpad platform identifier (e.g. `Pump.fun`, `pump_agent`) |
| `migrated_pool_exchange` | DEX the token migrated to, if any (e.g. `pump_amm`); empty if not migrated |
| `base_token.symbol` | Token ticker symbol |
| `base_token.logo` | Token logo image URL |
| `base_token.hot_level` | Hotness level (`0` = normal, higher = trending) |
| `base_token.total_supply` | Total token supply (string) |
| `base_token.token_create_time` | Unix timestamp when token was created |
| `base_token.token_open_time` | Unix timestamp when trading opened (`0` if not yet migrated/opened) |
| `maker_info.address` | Followed wallet address |
| `maker_info.name` | Wallet display name |
| `maker_info.twitter_username` | Twitter / X username |
| `maker_info.twitter_name` | Twitter / X display name |
| `maker_info.tags` | Array of wallet tags (e.g. `["kol","gmgn"]`) |
| `maker_info.tag_rank` | Map of tag → rank within that category (e.g. `{"kol": 854}`) |
| `balance_info` | Wallet token balance info; `null` if not available |

## `track kol` / `track smartmoney` Response Fields

Each item in `list` contains:

| Field | Description |
|-------|-------------|
| `transaction_hash` | On-chain transaction hash |
| `maker` | Wallet address of the trader (KOL / Smart Money) |
| `side` | Trade direction: `buy` or `sell` |
| `base_address` | Token contract address |
| `base_token.symbol` | Token ticker symbol |
| `base_token.launchpad` | Launchpad platform (e.g. `pump`) |
| `amount_usd` | Trade value in USD |
| `token_amount` | Token quantity traded |
| `price_usd` | Token price in USD at time of trade |
| `buy_cost_usd` | Original buy cost in USD (0 if this record is the buy) |
| `is_open_or_close` | `0` = position opened / added, `1` = position closed / reduced |
| `timestamp` | Unix timestamp of the trade |
| `maker_info.twitter_username` | KOL's Twitter username |
| `maker_info.tags` | Wallet tags (e.g. `kol`, `smart_degen`, `photon`) |

## Notes

- `track kol` / `track smartmoney` use normal auth (API Key only, no signature required)
- `track follow-wallet` requires `GMGN_PRIVATE_KEY` for signature auth — and wallets must be followed via the GMGN platform first
- Use `--raw` to get single-line JSON for further processing
- `track kol` / `track smartmoney` `--side` is a **client-side filter** — the CLI fetches all results then filters locally; it is NOT sent to the API
