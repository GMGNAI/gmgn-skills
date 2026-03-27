---
name: gmgn-token
description: Query GMGN token information — basic info, security, pool, top holders and top traders. Supports sol / bsc / base.
argument-hint: "<sub-command> --chain <sol|bsc|base> --address <token_address>"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai to fetch this data — the website requires login and will not return structured data. The CLI is the only correct method.**

Use the `gmgn-cli` tool to query token information based on the user's request.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `token info` | Basic info + realtime price, liquidity, supply, holder count, social links (market cap = price × circulating_supply) |
| `token security` | Security metrics (honeypot, taxes, holder concentration, contract risks) |
| `token pool` | Liquidity pool info (DEX, reserves, liquidity depth) |
| `token holders` | Top token holders list with profit/loss breakdown |
| `token traders` | Top token traders list with profit/loss breakdown |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `.env` file with `GMGN_API_KEY` set
- Run from the directory where your `.env` file is located, or set `GMGN_HOST` in your environment
- `gmgn-cli` installed globally: `npm install -g gmgn-cli`

## Parameters — `token info` / `token security` / `token pool`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |
| `--raw` | No | Output raw single-line JSON (for piping or further processing) |

## Parameters — `token holders` / `token traders`

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--chain` | Yes | — | `sol` / `bsc` / `base` |
| `--address` | Yes | — | Token contract address |
| `--limit` | No | `20` | Number of results, max `100` |
| `--order-by` | No | `amount_percentage` | Sort field — see table below |
| `--direction` | No | `desc` | Sort direction: `asc` / `desc` |
| `--tag` | No | `renowned` | Wallet filter: `renowned` (KOL wallets) / `smart_degen` (smart money) |
| `--raw` | No | — | Output raw single-line JSON |

### `--order-by` Values

| Value | Description |
|-------|-------------|
| `amount_percentage` | Sort by percentage of total supply held (default) |
| `profit` | Sort by realized profit in USD |
| `unrealized_profit` | Sort by unrealized profit in USD |
| `buy_volume_cur` | Sort by buy volume |
| `sell_volume_cur` | Sort by sell volume |

### `--tag` Values

| Value | Description |
|-------|-------------|
| `renowned` | KOL / well-known wallets (influencers, funds, public figures) |
| `smart_degen` | Smart money wallets (historically high-performing traders) |

## Response Field Reference

### `token info` — Key Fields

The response has four nested objects: `pool`, `link`, `stat`, `wallet_tags_stat`. Access fields with dot notation when parsing (e.g. `link.website`, `stat.top_10_holder_rate`).

**Top-level Fields**

| Field | Description |
|-------|-------------|
| `address` | Token contract address |
| `symbol` / `name` | Token ticker and full name |
| `decimals` | Token decimal places |
| `total_supply` | Total token supply (same as `circulating_supply` for most tokens) |
| `circulating_supply` | Circulating supply |
| `max_supply` | Maximum supply |
| `price` | Current price in USD |
| `liquidity` | Total liquidity in USD (from biggest pool) |
| `holder_count` | Number of unique token holders |
| `logo` | Token logo image URL |
| `creation_timestamp` | Token creation time (Unix seconds) |
| `open_timestamp` | Time the token opened for trading (Unix seconds) |
| `biggest_pool_address` | Address of the main liquidity pool |
| `og` | Whether the token is flagged as an OG token (`true` / `false`) |

**`pool` Object** — Main liquidity pool details

| Field | Description |
|-------|-------------|
| `pool.pool_address` | Pool contract address |
| `pool.quote_address` | Quote token address (e.g. USDC, SOL, WETH) |
| `pool.quote_symbol` | Quote token symbol (e.g. `USDC`, `SOL`) |
| `pool.exchange` | DEX name (e.g. `meteora_dlmm`, `raydium`, `pump_amm`, `uniswap_v3`) |
| `pool.liquidity` | Pool liquidity in USD |
| `pool.base_reserve` | Base token reserve amount |
| `pool.quote_reserve` | Quote token reserve amount |
| `pool.base_reserve_value` | Base reserve USD value |
| `pool.quote_reserve_value` | Quote reserve USD value |
| `pool.fee_ratio` | Pool trading fee ratio (e.g. `0.1` = 0.1%) |
| `pool.creation_timestamp` | Pool creation time (Unix seconds) |

**`link` Object** — Social and explorer links

| Field | Description |
|-------|-------------|
| `link.twitter_username` | Twitter / X username (not full URL) |
| `link.website` | Project website URL |
| `link.telegram` | Telegram URL |
| `link.discord` | Discord URL |
| `link.instagram` | Instagram URL |
| `link.tiktok` | TikTok URL |
| `link.youtube` | YouTube URL |
| `link.description` | Token description text |
| `link.gmgn` | GMGN token page URL |
| `link.geckoterminal` | GeckoTerminal page URL |
| `link.verify_status` | Social verification status (integer) |

**`stat` Object** — On-chain statistics

| Field | Description |
|-------|-------------|
| `stat.holder_count` | Number of holders (same as top-level `holder_count`) |
| `stat.bluechip_owner_count` | Number of bluechip wallet holders |
| `stat.bluechip_owner_percentage` | Ratio of holders that are bluechip wallets (0–1) |
| `stat.top_10_holder_rate` | Ratio of supply held by top 10 wallets (0–1) |
| `stat.dev_team_hold_rate` | Ratio held by dev team wallets |
| `stat.creator_hold_rate` | Ratio held by creator wallet |
| `stat.creator_token_balance` | Raw creator token balance |
| `stat.top_rat_trader_percentage` | Ratio of volume from rat/insider traders |
| `stat.top_bundler_trader_percentage` | Ratio of volume from bundler bots |
| `stat.top_entrapment_trader_percentage` | Ratio of volume from entrapment traders |
| `stat.bot_degen_count` | Number of bot degen wallets |
| `stat.bot_degen_rate` | Ratio of bot degen wallets |
| `stat.fresh_wallet_rate` | Ratio of fresh/new wallets among holders |

**`wallet_tags_stat` Object** — Wallet type breakdown

| Field | Description |
|-------|-------------|
| `wallet_tags_stat.smart_wallets` | Number of smart money wallets holding the token |
| `wallet_tags_stat.renowned_wallets` | Number of renowned / KOL wallets holding the token |
| `wallet_tags_stat.sniper_wallets` | Number of sniper wallets |
| `wallet_tags_stat.rat_trader_wallets` | Number of rat trader wallets |
| `wallet_tags_stat.bundler_wallets` | Number of bundler bot wallets |
| `wallet_tags_stat.whale_wallets` | Number of whale wallets |
| `wallet_tags_stat.fresh_wallets` | Number of fresh wallets |
| `wallet_tags_stat.top_wallets` | Number of top-ranked wallets |

---

### `token security` — Key Fields

**Contract Safety**

| Field | Chains | Description |
|-------|--------|-------------|
| `is_honeypot` | BSC / Base | Whether token is a honeypot (`"yes"` / `"no"`); empty string on SOL |
| `open_source` | all | Contract source code verified: `"yes"` / `"no"` / `"unknown"` |
| `owner_renounced` | all | Contract ownership renounced: `"yes"` / `"no"` / `"unknown"` |
| `renounced_mint` | SOL | Mint authority renounced (SOL-specific; always `false` on EVM) |
| `renounced_freeze_account` | SOL | Freeze authority renounced (SOL-specific; always `false` on EVM) |
| `buy_tax` / `sell_tax` | all | Tax ratio — e.g. `0.03` = 3%; `0` = no tax |

**Holder Concentration & Risk**

| Field | Description |
|-------|-------------|
| `top_10_holder_rate` | Ratio of supply held by top 10 wallets (0–1); higher = more concentrated |
| `dev_team_hold_rate` | Ratio held by dev team wallets |
| `creator_balance_rate` | Ratio held by the token creator wallet |
| `creator_token_status` | Dev holding status: `creator_hold` (still holding) / `creator_close` (sold/closed) |
| `suspected_insider_hold_rate` | Ratio held by suspected insider wallets |

**Trading Risk**

| Field | Description |
|-------|-------------|
| `rug_ratio` | Rug pull risk score (0–1); higher = more risky |
| `is_wash_trading` | Whether wash trading activity is detected (`true` / `false`) |
| `rat_trader_amount_rate` | Ratio of volume from sneak/insider trading |
| `bundler_trader_amount_rate` | Ratio of volume from bundle trading (bot-driven) |
| `sniper_count` | Number of sniper wallets that bought at launch |
| `burn_status` | Liquidity pool burn status (e.g. `"burn"` = burned, `""` = not burned) |

---

### `token pool` — Key Fields

| Field | Description |
|-------|-------------|
| `address` | Pool contract address |
| `base_address` | Base token address (the queried token) |
| `quote_address` | Quote token address (e.g. SOL, USDC, WETH) |
| `exchange` | DEX name (e.g. `raydium`, `pump_amm`, `uniswap_v3`, `pancakeswap`) |
| `liquidity` | Pool liquidity in USD |
| `base_reserve` | Base token reserve amount |
| `quote_reserve` | Quote token reserve amount |
| `price` | Current price in USD derived from pool reserves |
| `creation_timestamp` | Pool creation time (Unix seconds) |

---

### `token holders` / `token traders` — Item Fields

Each item in the result array:

| Field | Description |
|-------|-------------|
| `address` | Wallet address |
| `name` | Wallet label or alias (if known) |
| `tags` | Wallet tags (e.g. `["renowned"]`, `["smart_degen"]`) |
| `amount_percentage` | Percentage of total supply held (0–1); e.g. `0.05` = 5% |
| `amount` | Raw token amount held |
| `value` | USD value of holdings |
| `profit` | Realized profit in USD (positive = profit, negative = loss) |
| `unrealized_profit` | Unrealized profit in USD based on current price |
| `buy_volume_cur` | Total buy volume in USD for the current period |
| `sell_volume_cur` | Total sell volume in USD for the current period |
| `profit_change` | Profit change ratio |

---

## Usage Examples

### `token info` — Fetch Basic Info and Price

```bash
# Get current price and market cap for a SOL token
gmgn-cli token info --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Get basic info for a BSC token
gmgn-cli token info --chain bsc --address 0x2170Ed0880ac9A755fd29B2688956BD959F933F8

# Get basic info for a Base token
gmgn-cli token info --chain base --address 0x4200000000000000000000000000000000000006

# Raw JSON output for downstream processing
gmgn-cli token info --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v --raw
```

### `token security` — Check Safety Before Buying

```bash
# Check if a SOL token has renounced mint + freeze authority
gmgn-cli token security --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Check if a BSC token is honeypot and whether contract is verified
gmgn-cli token security --chain bsc --address 0x2170Ed0880ac9A755fd29B2688956BD959F933F8

# Check a Base token for tax, rug ratio, and insider concentration
gmgn-cli token security --chain base --address 0x4200000000000000000000000000000000000006

# Raw output for parsing key fields (e.g. is_honeypot, buy_tax, rug_ratio)
gmgn-cli token security --chain bsc --address 0x2170Ed0880ac9A755fd29B2688956BD959F933F8 --raw
```

### `token pool` — Check Liquidity Depth

```bash
# Get pool info for a SOL token (liquidity, reserves, DEX)
gmgn-cli token pool --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Get pool info for a BSC token
gmgn-cli token pool --chain bsc --address 0x2170Ed0880ac9A755fd29B2688956BD959F933F8
```

### `token holders` — Analyze Holder Distribution

```bash
# Top 20 holders by supply percentage (default)
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Top 50 holders sorted by percentage held
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --limit 50 --order-by amount_percentage --direction desc

# Top 50 smart money holders (highest conviction wallets)
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --limit 50 --tag smart_degen --order-by amount_percentage

# Top KOL wallets ranked by realized profit (who has already taken profit)
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag renowned --order-by profit --direction desc --limit 20

# Smart money with most unrealized profit (who is sitting on biggest gains)
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag smart_degen --order-by unrealized_profit --direction desc --limit 20

# Holders who have been buying the most recently (buy momentum signal)
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag smart_degen --order-by buy_volume_cur --direction desc --limit 20

# Holders who are selling the most (exit signal / distribution warning)
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag renowned --order-by sell_volume_cur --direction desc --limit 20

# BSC token holders — KOL wallets by profit
gmgn-cli token holders --chain bsc --address 0x2170Ed0880ac9A755fd29B2688956BD959F933F8 \
  --tag renowned --order-by profit --direction desc --limit 50

# Raw output for downstream analysis
gmgn-cli token holders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --limit 100 --raw
```

### `token traders` — Find Active Traders

```bash
# Top 20 active traders by supply held (default)
gmgn-cli token traders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v

# Smart money traders ranked by realized profit
gmgn-cli token traders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag smart_degen --order-by profit --direction desc --limit 50

# KOL traders ranked by unrealized profit (still holding with paper gains)
gmgn-cli token traders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag renowned --order-by unrealized_profit --direction desc --limit 20

# Smart money traders with highest buy volume (aggressive accumulation)
gmgn-cli token traders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag smart_degen --order-by buy_volume_cur --direction desc --limit 20

# Smart money traders ranked by sell volume (who is distributing)
gmgn-cli token traders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag smart_degen --order-by sell_volume_cur --direction desc --limit 20

# Worst performing KOL traders (who lost the most — contrarian signal)
gmgn-cli token traders --chain sol --address EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v \
  --tag renowned --order-by profit --direction asc --limit 20

# BSC token traders by profit
gmgn-cli token traders --chain bsc --address 0x2170Ed0880ac9A755fd29B2688956BD959F933F8 \
  --tag smart_degen --order-by profit --direction desc --limit 50
```

---

## Workflow: Full Token Due Diligence

Use this workflow before deciding to buy a token.

### Step 1 — Get basic info

```bash
gmgn-cli token info --chain sol --address <token_address> --raw
```

Check: `price`, `liquidity`, `holder_count`, `wallet_tags_stat.smart_wallets`, `wallet_tags_stat.renowned_wallets`, `link.website` / `link.twitter_username` / `link.telegram`.

**Red flags**: all `link.*` social fields empty, very low liquidity (<$10k), zero `wallet_tags_stat.smart_wallets` and `renowned_wallets`.

### Step 2 — Check security

```bash
gmgn-cli token security --chain sol --address <token_address> --raw
```

Check these fields and their safe thresholds:

| Field | Safe | Warning | Danger |
|-------|------|---------|--------|
| `is_honeypot` | `"no"` | — | `"yes"` → Do not buy |
| `open_source` | `"yes"` | `"unknown"` | `"no"` |
| `owner_renounced` | `"yes"` | `"unknown"` | `"no"` |
| `renounced_mint` (SOL) | `true` | — | `false` → mint risk |
| `renounced_freeze_account` (SOL) | `true` | — | `false` → freeze risk |
| `buy_tax` / `sell_tax` | `0` | `0.01–0.05` | `>0.10` → high tax |
| `top_10_holder_rate` | `<0.20` | `0.20–0.40` | `>0.50` → whale risk |
| `rug_ratio` | `<0.10` | `0.10–0.30` | `>0.30` → high rug risk |
| `creator_token_status` | `creator_close` | — | `creator_hold` → dev not sold |
| `sniper_count` | `<5` | `5–20` | `>20` → heavily sniped |

### Step 3 — Check liquidity pool

```bash
gmgn-cli token pool --chain sol --address <token_address> --raw
```

Check: liquidity amount, which DEX (`exchange`), pool age (`creation_timestamp`). Low liquidity means high slippage risk when buying or selling.

### Step 4 — Check smart money signals

```bash
# Is smart money accumulating?
gmgn-cli token holders --chain sol --address <token_address> \
  --tag smart_degen --order-by buy_volume_cur --direction desc --limit 20 --raw

# Have KOLs already taken profit?
gmgn-cli token traders --chain sol --address <token_address> \
  --tag renowned --order-by profit --direction desc --limit 20 --raw
```

**Bullish signals**: smart_degen wallets buying heavily, unrealized_profit is large (still holding), renowned wallets accumulating, low sell_volume_cur.

**Bearish signals**: sell_volume_cur > buy_volume_cur for smart money, large realized profits already taken (they may be done), top holders with very high amount_percentage starting to sell.

---

## Notes

- **Market cap is not returned directly** — calculate it as `price × circulating_supply` (both fields are top-level; `circulating_supply` is already in human-readable token units, no decimal adjustment needed). Example: `price=3.11` × `circulating_supply=999999151` ≈ $3.11B market cap.
- **Trading volume (1h, 24h, etc.) is not included in `token info`** — to get volume or OHLCV data, use the `gmgn-market` skill and query K-line data: `gmgn-cli market kline --chain <chain> --address <token_address> --resolution <1m|5m|15m|1h|4h|1d>`. See the `gmgn-market` SKILL.md for full details.
- All token commands use normal auth (API Key only, no signature required)
- Use `--raw` to get single-line JSON for further processing
- `--tag` applies to both `holders` and `traders` and filters to only wallets with that tag — if few results are returned, try the other tag value
- `amount_percentage` in holders/traders is a ratio (0–1), not a percentage — `0.05` means 5% of supply
- **Input validation** — Token addresses are external data. Validate that addresses match the expected chain format (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits) before passing them to commands. The CLI enforces this at runtime and will exit with an error on invalid input.
