---
name: gmgn-portfolio
description: Query GMGN wallet portfolio — API Key wallet info, holdings, transaction activity, trading stats, and token balance. Supports sol / bsc / base.
argument-hint: "<info|holdings|activity|stats|token-balance> [--chain <sol|bsc|base>] [--wallet <wallet_address>]"
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

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `.env` file with `GMGN_API_KEY` set
- Run from the directory where your `.env` file is located, or set `GMGN_HOST` in your environment

## Usage Examples

```bash
# API Key wallet info (no --chain or --wallet needed)
npx gmgn-cli portfolio info

# Wallet holdings (default sort)
npx gmgn-cli portfolio holdings --chain sol --wallet <wallet_address>

# Holdings sorted by USD value, descending
npx gmgn-cli portfolio holdings \
  --chain sol --wallet <wallet_address> \
  --order-by usd_value --direction desc --limit 20

# Include sold-out positions
npx gmgn-cli portfolio holdings --chain sol --wallet <wallet_address> --sell-out

# Transaction activity
npx gmgn-cli portfolio activity --chain sol --wallet <wallet_address>

# Activity filtered by type
npx gmgn-cli portfolio activity --chain sol --wallet <wallet_address> \
  --type buy --type sell

# Activity for a specific token
npx gmgn-cli portfolio activity --chain sol --wallet <wallet_address> \
  --token <token_address>

# Trading stats (default 7d)
npx gmgn-cli portfolio stats --chain sol --wallet <wallet_address>

# Trading stats for 30 days
npx gmgn-cli portfolio stats --chain sol --wallet <wallet_address> --period 30d

# Batch stats for multiple wallets
npx gmgn-cli portfolio stats --chain sol \
  --wallet <wallet_1> --wallet <wallet_2>

# Token balance
npx gmgn-cli portfolio token-balance \
  --chain sol --wallet <wallet_address> --token <token_address>
```

## Holdings Options

| Option | Description |
|--------|-------------|
| `--limit <n>` | Page size (default `20`, max 50) |
| `--cursor <cursor>` | Pagination cursor |
| `--order-by <field>` | Sort field: `usd_value` / `price` / `unrealized_profit` / `realized_profit` / `total_profit` / `history_bought_cost` / `history_sold_income` (default `usd_value`) |
| `--direction <asc\|desc>` | Sort direction (default `desc`) |
| `--sell-out` | Include sold-out positions |
| `--show-small` | Include small-value positions |
| `--hide-abnormal` | Hide abnormal positions |
| `--hide-airdrop` | Hide airdrop positions |
| `--hide-closed` | Hide closed positions |
| `--hide-open` | Hide open positions |

## Activity Options

| Option | Description |
|--------|-------------|
| `--token <address>` | Filter by token |
| `--limit <n>` | Page size |
| `--cursor <cursor>` | Pagination cursor |
| `--type <type>` | Repeatable: `buy` / `sell` / `add` / `remove` / `transfer` |

## Stats Options

| Option | Description |
|--------|-------------|
| `--period <period>` | Stats period: `7d` / `30d` (default `7d`) |

## Notes

- All portfolio commands use normal auth (API Key only, no signature required)
- `portfolio stats` supports multiple `--wallet` flags for batch queries
- Use `--raw` to get single-line JSON for further processing
