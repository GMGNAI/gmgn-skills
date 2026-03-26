---
name: gmgn-portfolio
description: Query GMGN wallet portfolio — API Key wallet info, holdings, transaction activity, trading stats, token balance, follow-wallet trades, KOL trades, and Smart Money trades. Supports sol / bsc / base.
argument-hint: "<info|holdings|activity|stats|token-balance|follow-wallet|kol|smartmoney> [--chain <sol|bsc|base>] [--wallet <wallet_address>]"
---

Use the `gmgn-cli` tool to query wallet portfolio data based on the user's request.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `portfolio info` | Wallets and main currency balances bound to the API Key |
| `portfolio holdings` | Wallet token holdings with P&L |
| `portfolio activity` | Transaction history |
| `portfolio stats` | Trading statistics (supports batch) |
| `portfolio token-balance` | Token balance for a specific token |
| `portfolio follow-wallet` | Follow-wallet trade records |
| `portfolio kol` | KOL trade records (SOL chain) |
| `portfolio smartmoney` | Smart Money trade records (SOL chain) |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `.env` file with `GMGN_API_KEY` set
- Run from the directory where your `.env` file is located, or set `GMGN_HOST` in your environment
- `gmgn-cli` installed globally: `npm install -g gmgn-cli@1.1.0`

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
| `--sell-out` | Include sold-out positions |
| `--show-small` | Include small-value positions |
| `--hide-abnormal` | Hide abnormal positions |
| `--hide-airdrop` | Hide airdrop positions |
| `--hide-closed` | Hide closed positions |
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

## `portfolio follow-wallet` Options

| Option | Description |
|--------|-------------|
| `--chain` | Required. `sol` / `bsc` / `base` / `eth` |
| `--wallet <address>` | Filter by wallet address |
| `--base-token <address>` | Filter by base token address |
| `--page-token <cursor>` | Pagination cursor |
| `--limit <n>` | Page size (1–200, default 100) |
| `--side <side>` | Trade direction filter |
| `--cost <cost>` | Cost filter |
| `--filter <tag...>` | Repeatable filter conditions |
| `--with-balance` | Include balance in response |
| `--with-security` | Include security info in response |
| `--min-amount-usd <n>` | Minimum trade amount (USD) |
| `--max-amount-usd <n>` | Maximum trade amount (USD) |
| `--is-gray` | Gray mode filter |

## `portfolio kol` / `portfolio smartmoney` Options

| Option | Description |
|--------|-------------|
| `--limit <n>` | Page size (1–200, default 100) |

Both `kol` and `smartmoney` return SOL chain data only — no `--chain` flag needed.

```bash
# Follow-wallet trades filtered by wallet
gmgn-cli portfolio follow-wallet --chain sol --wallet <wallet_address>

# Follow-wallet with balance info
gmgn-cli portfolio follow-wallet --chain sol --with-balance --limit 20

# KOL trade records
gmgn-cli portfolio kol --limit 10 --raw

# Smart Money trade records
gmgn-cli portfolio smartmoney --limit 10 --raw
```

## Notes

- All portfolio commands use normal auth (API Key only, no signature required)
- `portfolio stats` supports multiple `--wallet` flags for batch queries
- Use `--raw` to get single-line JSON for further processing
- **Input validation** — Wallet and token addresses are validated against the expected chain format at runtime (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits). The CLI exits with an error on invalid input.
