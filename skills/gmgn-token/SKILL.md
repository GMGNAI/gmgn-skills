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

## Usage Examples

```bash
# Basic token info
npx gmgn-cli token info --chain sol --address <token_address>

# Security metrics
npx gmgn-cli token security --chain sol --address <token_address>

# Liquidity pool
npx gmgn-cli token pool --chain sol --address <token_address>

# Top holders
npx gmgn-cli token holders --chain sol --address <token_address>
npx gmgn-cli token holders --chain sol --address <token_address> --limit 50

# Top traders
npx gmgn-cli token traders --chain sol --address <token_address>
npx gmgn-cli token traders --chain sol --address <token_address> --limit 50

# Raw JSON output (for piping)
npx gmgn-cli token info --chain sol --address <token_address> --raw
```

## Notes

- All token commands use normal auth (API Key only, no signature required)
- Use `--raw` to get single-line JSON for further processing
