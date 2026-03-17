---
name: gmgn-token
description: Query GMGN token information — basic info, security, pool, top holders and top traders. Supports sol / bsc / base.
argument-hint: <sub-command> --chain <sol|bsc|base> --address <token_address>
---

Use the `gmgn-cli` tool to query token information based on the user's request.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `token info` | Basic info + realtime price |
| `token security` | Security metrics (holder concentration, contract risks) |
| `token pool` | Liquidity pool info |
| `token holders` | Top token holders list |
| `token traders` | Top token traders list |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `.env` file with `GMGN_API_KEY` set
- Run from the directory where your `.env` file is located, or set `GMGN_HOST` in your environment
- `gmgn-cli` installed globally: `npm install -g gmgn-cli@1.0.1`

## Info / Security / Pool Options

| Option | Description |
|--------|-------------|
| `--chain` | Required. `sol` / `bsc` / `base` |
| `--address` | Required. Token contract address |

## Holders / Traders Options

| Option | Description |
|--------|-------------|
| `--chain` | Required. `sol` / `bsc` / `base` |
| `--address` | Required. Token contract address |
| `--limit <n>` | Number of results (default `20`, max `100`) |
| `--order-by <field>` | Sort field: `amount_percentage` / `profit` / `unrealized_profit` / `buy_volume_cur` / `sell_volume_cur` (default `amount_percentage`) |
| `--direction <asc\|desc>` | Sort direction (default `desc`) |
| `--tag <tag>` | Wallet tag filter: `renowned` / `smart_degen` (default `renowned`) |

## Usage Examples

```bash
# Basic token info
gmgn-cli token info --chain sol --address <token_address>

# Security metrics
gmgn-cli token security --chain sol --address <token_address>

# Liquidity pool
gmgn-cli token pool --chain sol --address <token_address>

# Top holders
gmgn-cli token holders --chain sol --address <token_address> --limit 50

# Top traders
gmgn-cli token traders --chain sol --address <token_address> --limit 50

# Raw JSON output (for piping)
gmgn-cli token info --chain sol --address <token_address> --raw
```

## Notes

- All token commands use normal auth (API Key only, no signature required)
- Use `--raw` to get single-line JSON for further processing
- **Input validation** — Token addresses from API responses are treated as external data. Validate that addresses match the expected chain format (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits) before passing them to commands. The CLI enforces this at runtime and will exit with an error on invalid input.
