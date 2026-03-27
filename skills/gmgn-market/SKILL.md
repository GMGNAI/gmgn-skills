---
name: gmgn-market
description: Query GMGN market data — token K-line (candlestick), trending token swap data, and Trenches token lists. Supports sol / bsc / base.
argument-hint: "kline --chain <sol|bsc|base> --address <token_address> --resolution <1m|5m|15m|1h|4h|1d> [--from <unix_ts>] [--to <unix_ts>] | trending --chain <sol|bsc|base> --interval <1m|5m|1h|6h|24h> | trenches --chain <sol|bsc|base>"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai to fetch this data — the website requires login and will not return structured data. The CLI is the only correct method.**

**⚠️ IPv6 NOT SUPPORTED: GMGN CLI commands do not support IPv6. If you get a `401` or `403` error and credentials look correct, the outbound connection is likely going via IPv6. Run `curl -s https://api64.ipify.org` to check — if the result is an IPv6 address, tell the user to ensure their network routes requests over IPv4.**

Use the `gmgn-cli` tool to query K-line data for a token, browse trending tokens, or view Trenches token lists.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `market kline` | Token candlestick / OHLCV data and trading volume over a time range |
| `market trending` | Trending tokens ranked by swap activity — use `--interval` to specify the time window (e.g. `1m` for 1-minute hottest, `1h` for 1-hour trending) |
| `market trenches` | Newly launched launchpad paltform tokens — **use this when the user asks for "new tokens", "just launched tokens", "latest tokens on pump.fun/letsbonk"**. Three categories: `new_creation` (just created), `near_completion` (bonding curve almost full), `completed` (graduated to open market / DEX) |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `.env` file with `GMGN_API_KEY` set
- Run from the directory where your `.env` file is located, or set `GMGN_HOST` in your environment
- `gmgn-cli` installed globally: `npm install -g gmgn-cli`

## `market kline` Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--address` | Yes | Token contract address |
| `--resolution` | Yes | Candlestick resolution: `1m` / `5m` / `15m` / `1h` / `4h` / `1d` |
| `--from` | No | Start time (Unix seconds) |
| `--to` | No | End time (Unix seconds) |

## `market kline` Response Fields

The response is an object with a `list` array. Each element in `list` is one candlestick:

| Field | Type | Description |
|-------|------|-------------|
| `time` | number | Candle open time — Unix timestamp in **milliseconds** (divide by 1000 for seconds) |
| `open` | string | Opening price in USD at the start of the period |
| `close` | string | Closing price in USD at the end of the period |
| `high` | string | Highest price in USD during the period |
| `low` | string | Lowest price in USD during the period |
| `volume` | string | Trading volume in **USD** (dollar value of all trades in this period) |
| `amount` | string | Trading volume in **base token units** (number of tokens traded) |

**Important distinctions (naming is counterintuitive — do not guess):**
- `volume` = USD dollar value (e.g. `1214` means ~$1,214 traded) — use this for "how much was traded in USD"
- `amount` = token count (e.g. `5379110` means ~5.38M tokens changed hands) — use this for "how many tokens were traded"
- For tokens not priced at $1, `volume` and `amount` will differ by orders of magnitude (e.g. a $0.0002 token: $1,214 volume = 5,379,110 tokens)
- To get **total USD volume over a time range**, sum `volume` across all candles in the range
- To get **price trend**, read `close` values in chronological order (`time` ascending)
- To detect **volatility**, compare `high` vs `low` within each candle
- Candles are returned in chronological order (oldest first)

## `market trending` Options

**`--interval` selection guide — always match to the user's stated time window:**

| User says | `--interval` |
|-----------|-------------|
| "1分钟热门" / "1m trending" / "hottest right now" | `1m` |
| "5分钟" / "5m" | `5m` |
| "1小时" / "1h" / no time specified (default) | `1h` |
| "6小时" / "6h" | `6h` |
| "24小时" / "今日" / "daily" | `24h` |

| Option | Description |
|--------|-------------|
| `--chain` | Required. `sol` / `bsc` / `base` |
| `--interval` | Required. `1m` / `5m` / `1h` / `6h` / `24h` (default `1h`) |
| `--limit <n>` | Number of results (default 100, max 100) |
| `--order-by <field>` | Sort field: `default` / `swaps` / `marketcap` / `history_highest_market_cap` / `liquidity` / `volume` / `holder_count` / `smart_degen_count` / `renowned_count` / `gas_fee` / `price` / `change1m` / `change5m` / `change1h` / `creation_timestamp` |
| `--direction <asc\|desc>` | Sort direction (default `desc`) |
| `--filter <tag...>` | Repeatable filter tags (chain-specific). **sol** (defaults: `renounced frozen`): `renounced` / `frozen` / `burn` / `token_burnt` / `has_social` / `not_social_dup` / `not_image_dup` / `dexscr_update_link` / `not_wash_trading` / `is_internal_market` / `is_out_market`. **evm** (defaults: `not_honeypot verified renounced`): `not_honeypot` / `verified` / `renounced` / `locked` / `token_burnt` / `has_social` / `not_social_dup` / `not_image_dup` / `dexscr_update_link` / `is_internal_market` / `is_out_market` |
| `--platform <name...>` | Repeatable platform filter (chain-specific). **sol**: `Pump.fun` / `pump_mayhem` / `pump_mayhem_agent` / `pump_agent` / `letsbonk` / `bonkers` / `bags` / `memoo` / `liquid` / `bankr` / `zora` / `surge` / `anoncoin` / `moonshot_app` / `wendotdev` / `heaven` / `sugar` / `token_mill` / `believe` / `trendsfun` / `trends_fun` / `jup_studio` / `Moonshot` / `boop` / `xstocks` / `ray_launchpad` / `meteora_virtual_curve` / `pool_ray` / `pool_meteora` / `pool_pump_amm` / `pool_orca`. **bsc**: `fourmeme` / `fourmeme_agent` / `bn_fourmeme` / `flap` / `clanker` / `lunafun` / `pool_uniswap` / `pool_pancake`. **base**: `clanker` / `bankr` / `flaunch` / `zora` / `zora_creator` / `baseapp` / `basememe` / `virtuals_v2` / `klik` |

## Usage Examples

### Kline

```bash
# Last 1 hour of 1-minute candles
# macOS:
gmgn-cli market kline \
  --chain sol \
  --address <token_address> \
  --resolution 1m \
  --from $(date -v-1H +%s) \
  --to $(date +%s)
# Linux: use $(date -d '1 hour ago' +%s) instead of $(date -v-1H +%s)

# Last 24 hours of 1-hour candles
# macOS:
gmgn-cli market kline \
  --chain sol \
  --address <token_address> \
  --resolution 1h \
  --from $(date -v-24H +%s) \
  --to $(date +%s)
# Linux: use $(date -d '24 hours ago' +%s) instead of $(date -v-24H +%s)

# Raw output for further processing
gmgn-cli market kline --chain sol --address <addr> \
  --resolution 5m --from <ts> --to <ts> --raw | jq '.[]'
```

### Trending — General

```bash
# Top 20 hot tokens on SOL in the last 1 hour, sorted by volume
gmgn-cli market trending --chain sol --interval 1h --order-by volume --limit 20

# Top 50 tokens on SOL, 5m window, sorted by volume
gmgn-cli market trending --chain sol --interval 5m --order-by volume --limit 50

# Hot tokens with social links only, verified and not honeypot, on BSC over 24h
gmgn-cli market trending \
  --chain bsc --interval 24h \
  --filter has_social --filter not_honeypot --filter verified
```

### Trending — SOL by Launchpad Platform

Use `--platform` to filter trending results to tokens from specific launchpads only.

```bash
# SOL 1m hottest — Pump.fun + letsbonk only (most active launchpads), sorted by volume
gmgn-cli market trending \
  --chain sol --interval 1m \
  --platform Pump.fun --platform letsbonk \
  --order-by volume --limit 50 --raw

# SOL 5m hottest — Pump.fun + letsbonk + Moonshot, sorted by volume
gmgn-cli market trending \
  --chain sol --interval 5m \
  --platform Pump.fun --platform letsbonk --platform moonshot_app \
  --order-by volume --limit 50 --raw

# SOL 1h trending — Pump.fun only, with safety filters
gmgn-cli market trending \
  --chain sol --interval 1h \
  --platform Pump.fun \
  --filter renounced --filter frozen --filter not_wash_trading \
  --order-by volume --limit 20 --raw

# SOL 1h trending — all major launchpads combined
gmgn-cli market trending \
  --chain sol --interval 1h \
  --platform Pump.fun --platform letsbonk --platform moonshot_app \
  --platform pump_mayhem --platform pump_mayhem_agent --platform bonkers \
  --order-by volume --limit 50 --raw
```

### Trending — BSC by Launchpad Platform

```bash
# BSC 1m hottest — fourmeme (main BSC launchpad), sorted by volume
gmgn-cli market trending \
  --chain bsc --interval 1m \
  --platform fourmeme --platform four_xmode_agent \
  --order-by volume --limit 50 --raw

# BSC 5m hottest — fourmeme family, sorted by volume
gmgn-cli market trending \
  --chain bsc --interval 5m \
  --platform fourmeme --platform fourmeme_agent --platform bn_fourmeme --platform four_xmode_agent \
  --order-by volume --limit 50 --raw

# BSC 1h trending — fourmeme with safety filters
gmgn-cli market trending \
  --chain bsc --interval 1h \
  --platform fourmeme --platform fourmeme_agent --platform bn_fourmeme --platform four_xmode_agent \
  --filter not_honeypot --filter verified \
  --order-by volume --limit 20 --raw
```

### Trending — Base by Launchpad Platform

```bash
# Base 1m hottest — clanker + zora (main Base launchpads), sorted by volume
gmgn-cli market trending \
  --chain base --interval 1m \
  --platform clanker --platform zora --platform zora_creator \
  --order-by volume --limit 50 --raw

# Base 5m hottest — clanker + zora + virtuals_v2 + flaunch, sorted by volume
gmgn-cli market trending \
  --chain base --interval 5m \
  --platform clanker --platform zora --platform zora_creator \
  --platform virtuals_v2 --platform flaunch \
  --order-by volume --limit 50 --raw

# Base 1h trending — all major launchpads with safety filters
gmgn-cli market trending \
  --chain base --interval 1h \
  --platform clanker --platform zora --platform zora_creator \
  --platform virtuals_v2 --platform flaunch --platform baseapp \
  --filter not_honeypot --filter verified \
  --order-by volume --limit 20 --raw
```

## `market trending` Response Fields

The response is `data.rank` — an array of rank items. Each item represents one token.

**Basic Info**

| Field | Description |
|-------|-------------|
| `address` | Token contract address |
| `symbol` / `name` | Token ticker and full name |
| `logo` | Token logo image URL |
| `chain` | Chain identifier |
| `total_supply` | Total token supply |
| `creator` | Creator wallet address |
| `launchpad_platform` | Launch/pool platform (e.g. `Pump.fun`, `letsbonk`, `pool_meteora`, `fourmeme`) |
| `exchange` | Current DEX (e.g. `meteora_damm_v2`, `raydium`, `pump_amm`) |
| `open_timestamp` | Open market listing time (Unix seconds) |
| `creation_timestamp` | Token creation time (Unix seconds) |
| `rank` | Position in this trending list (lower = hotter) |
| `hot_level` | Trending intensity level (higher = hotter) |

**Price & Market**

| Field | Description |
|-------|-------------|
| `price` | Current price in USD |
| `market_cap` | Market cap in USD (directly available — no calculation needed) |
| `liquidity` | Current liquidity in USD |
| `volume` | Trading volume in USD for the queried interval |
| `history_highest_market_cap` | All-time highest market cap in USD |
| `initial_liquidity` | Initial liquidity at token launch |
| `price_change_percent` | Price change % for the queried interval |
| `price_change_percent1m` | Price change % in last 1 minute |
| `price_change_percent5m` | Price change % in last 5 minutes |
| `price_change_percent1h` | Price change % in last 1 hour |

**Trading Activity**

| Field | Description |
|-------|-------------|
| `swaps` | Total swap count in the queried interval |
| `buys` / `sells` | Buy / sell count in the interval |
| `holder_count` | Number of unique token holders |
| `gas_fee` | Average gas fee per transaction |

**Security & Risk**

| Field | Chains | Description |
|-------|--------|-------------|
| `renounced_mint` | SOL | Mint authority renounced (`1` = yes, `0` = no) |
| `renounced_freeze_account` | SOL | Freeze authority renounced (`1` = yes, `0` = no) |
| `is_honeypot` | BSC / Base | Honeypot flag (`1` = yes, `0` = no) |
| `is_open_source` | all | Contract verified (`1` = yes, `0` = no) |
| `is_renounced` | all | Ownership renounced (`1` = yes, `0` = no) |
| `buy_tax` / `sell_tax` | all | Tax rate — empty string means `0` (no tax) |
| `burn_status` | all | Liquidity burn status (e.g. `"none"`, `"burn"`) |
| `top_10_holder_rate` | all | Top 10 wallets concentration (0–1) |
| `rug_ratio` | all | Rug pull risk score (0–1) |
| `is_wash_trading` | all | Wash trading detected (`true` / `false`) |
| `rat_trader_amount_rate` | all | Ratio of insider/sneak trading volume |
| `bundler_rate` | all | Ratio of bundle bot trading volume |
| `entrapment_ratio` | all | Entrapment trading ratio |
| `sniper_count` | all | Number of sniper wallets at launch |
| `bot_degen_count` / `bot_degen_rate` | all | Bot degen wallet count / ratio |
| `dev_team_hold_rate` | all | Dev team holding ratio |
| `top70_sniper_hold_rate` | all | Top 70 sniper current holding ratio |
| `lock_percent` | all | Liquidity lock percentage |

**Dev Status**

| Field | Description |
|-------|-------------|
| `creator_token_status` | Dev holding status: `creator_hold` (still holding) / `creator_close` (sold/closed) |
| `creator_close` | Boolean shorthand for `creator_token_status == creator_close` |
| `dev_token_burn_ratio` | Ratio of dev's tokens that have been burned |

**Smart Money**

| Field | Description |
|-------|-------------|
| `smart_degen_count` | Number of smart money wallets holding the token |
| `renowned_count` | Number of renowned / KOL wallets holding the token |
| `bluechip_owner_percentage` | Ratio of holders that are bluechip wallets (0–1) |

**Social**

| Field | Description |
|-------|-------------|
| `twitter_username` | Twitter / X username (not a full URL — prepend `https://x.com/` to get the link) |
| `website` | Project website URL |
| `telegram` | Telegram URL |
| `cto_flag` | Community takeover flag (`1` = CTO has occurred) |

**Dexscreener Marketing**

| Field | Description |
|-------|-------------|
| `dexscr_ad` | Dexscreener ad placed (`1` = yes) |
| `dexscr_update_link` | Social links updated on Dexscreener (`1` = yes) |
| `dexscr_trending_bar` | Paid for Dexscreener trending bar (`1` = yes) |
| `dexscr_boost_fee` | Dexscreener boost amount paid (0 = none) |

---

## Workflow: Discover Trading Opportunities via Trending

### Step 1 — Fetch trending data

Fetch a broad pool with safe filters:

```bash
gmgn-cli market trending \
  --chain <chain> --interval 1h \
  --order-by volume --limit 50 \
  --filter not_honeypot --filter has_social --raw
```

### Step 2 — AI multi-factor analysis

Analyze each record in the response using the following signals (apply judgment, not rigid rules):

| Signal | Field(s) | Weight | Notes |
|--------|----------|--------|-------|
| Smart money interest | `smart_degen_count`, `renowned_count` | High | Key conviction indicator |
| Bluechip ownership | `bluechip_owner_percentage` | Medium | Quality of holder base |
| Real trading activity | `volume`, `swaps` | Medium | Distinguishes genuine interest from wash trading |
| Price momentum | `change1h`, `change5m` | Medium | Prefer positive, non-parabolic moves |
| Pool safety | `liquidity` | Medium | Low liquidity = high slippage risk |
| Token maturity | `creation_timestamp` | Low | Avoid tokens less than ~1h old unless other signals are very strong |

Select the **top 5** tokens with the best composite profile. Prefer tokens that perform well across multiple signals rather than excelling in just one.

### Step 3 — Present top 5 to user

Present results as a concise table, then give a one-line rationale for each pick:

```
Top 5 Trending Tokens — SOL / 1h

# | Symbol | Address (short) | Smart Degens | Volume | 1h Chg | Reasoning
1 | ...     | ...             | ...          | ...    | ...    | Smart money accumulating + high volume
2 | ...
...
```

### Step 4 — Follow-up actions

For each token, offer:
- **Deep dive**: `token info` + `token security` for full due diligence
- **Swap**: execute directly if the user is satisfied with the trending data alone

## `market trenches` Parameters

**Intent → `--type` mapping (always specify `--type` explicitly):**

| User intent | `--type` value |
|-------------|----------------|
| "new tokens", "just launched", "newly created", "latest tokens" | `new_creation` |
| "about to graduate", "near completion", "bonding curve almost full" | `near_completion` |
| "graduated tokens", "already on DEX", "open market tokens" | `completed` |
| No specific stage mentioned | omit `--type` (returns all three) |

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--chain` | Yes | `sol` / `bsc` / `base` |
| `--type` | No | Categories to query, repeatable: `new_creation` / `near_completion` / `completed` (default: all three) |
| `--launchpad-platform` | No | Launchpad platform filter, repeatable (default: all platforms for the chain) |
| `--limit` | No | Max results per category, max 80 (default: 80) |

Response fields: `data.new_creation`, `data.pump`, `data.completed` — each is an array of `RankItem` (same fields as `market trending` rank items). **Important: `data.pump` in the response corresponds to `--type near_completion` in the request. The API always returns this category under the key `pump`, not `near_completion`.**

## `market trenches` Response Fields

**Basic Info**

| Field | Description |
|-------|-------------|
| `address` | Token contract address |
| `symbol` / `name` | Token symbol and name |
| `launchpad_platform` | Launch platform (e.g. `Pump.fun`, `letsbonk`) |
| `exchange` | Current exchange (e.g. `pump_amm`, `raydium`) |
| `usd_market_cap` | Market cap in USD |
| `liquidity` | Liquidity in USD |
| `total_supply` | Total token supply |
| `created_timestamp` | Creation time (Unix seconds) |
| `open_timestamp` | Open market listing time (Unix seconds, `completed` only) |
| `complete_timestamp` | Bonding curve completion time (Unix seconds) |
| `complete_cost_time` | Time from creation to completion in seconds |

**Trading Data**

| Field | Description |
|-------|-------------|
| `swaps_1m` / `swaps_1h` / `swaps_24h` | Swap count per time window |
| `volume_1h` / `volume_24h` | Trading volume in USD |
| `buys_24h` / `sells_24h` | Buy / sell count in 24h |
| `net_buy_24h` | Net buy volume in 24h |
| `holder_count` | Number of token holders |

**Security & Risk**

| Field | Chains | Description |
|-------|--------|-------------|
| `renounced_mint` | SOL | Whether mint authority is renounced (SOL-specific concept; always `false` on EVM chains) |
| `renounced_freeze_account` | SOL | Whether freeze authority is renounced (SOL-specific concept; always `false` on EVM chains) |
| `burn_status` | all | Liquidity burn status |
| `rug_ratio` | all | Rug pull risk ratio |
| `top_10_holder_rate` | all | Top 10 holders concentration ratio |
| `rat_trader_amount_rate` | all | Insider / sneak trading volume ratio |
| `bundler_trader_amount_rate` | all | Bundle trading volume ratio |
| `is_wash_trading` | all | Whether wash trading is detected |
| `sniper_count` | all | Number of sniper wallets |
| `suspected_insider_hold_rate` | all | Suspected insider holding ratio |
| `open_source` | all | Whether contract source code is verified (`"yes"` / `"no"` / `"unknown"`) |
| `owner_renounced` | all | Whether contract ownership is renounced (`"yes"` / `"no"` / `"unknown"`) |
| `is_honeypot` | BSC / Base | Whether token is a honeypot (`"yes"` / `"no"`); returns empty string on SOL (not applicable) |
| `buy_tax` | all | Buy tax ratio (e.g. `0.03` = 3%) |
| `dev_team_hold_rate` | all | Dev team holding ratio |

**Dev Holdings**

| Field | Description |
|-------|-------------|
| `creator_token_status` | Dev holding status (e.g. `creator_hold`, `creator_close`) |
| `creator_balance_rate` | Dev holding ratio as a proportion of total supply |

**Smart Money**

| Field | Description |
|-------|-------------|
| `smart_degen_count` | Number of smart money holders |
| `renowned_count` | Number of renowned wallet holders (KOL) |

**Social Media**

| Field | Description |
|-------|-------------|
| `twitter` | Twitter / X link |
| `telegram` | Telegram link |
| `website` | Website link |
| `instagram` | Instagram link |
| `tiktok` | TikTok link |
| `has_at_least_one_social` | Whether any social media link exists |
| `x_user_follower` | Twitter follower count |
| `cto_flag` | Whether community takeover (CTO) has occurred |

**Dexscreener Marketing**

| Field | Description |
|-------|-------------|
| `dexscr_ad` | Whether a Dexscreener ad has been placed |
| `dexscr_update_link` | Whether social links have been updated on Dexscreener |
| `dexscr_trending_bar` | Whether paid for Dexscreener trending bar placement |
| `dexscr_boost_fee` | Amount paid for Dexscreener boost (0 = none) |

### Solana Trenches Examples

```bash
# All three categories at once
gmgn-cli market trenches --chain sol --raw \
  --type new_creation --type near_completion --type completed \
  --launchpad-platform Pump.fun --launchpad-platform pump_mayhem --launchpad-platform pump_mayhem_agent --launchpad-platform pump_agent --launchpad-platform letsbonk --launchpad-platform bonkers --launchpad-platform bags \
  --limit 80

# New creation only
gmgn-cli market trenches --chain sol --raw \
  --type new_creation \
  --launchpad-platform Pump.fun --launchpad-platform pump_mayhem --launchpad-platform pump_mayhem_agent --launchpad-platform pump_agent --launchpad-platform letsbonk --launchpad-platform bonkers --launchpad-platform bags \
  --limit 80

# Near completion only
gmgn-cli market trenches --chain sol --raw \
  --type near_completion \
  --launchpad-platform Pump.fun --launchpad-platform pump_mayhem --launchpad-platform pump_mayhem_agent --launchpad-platform pump_agent --launchpad-platform letsbonk --launchpad-platform bonkers --launchpad-platform bags \
  --limit 80

# Completed (open market) only
gmgn-cli market trenches --chain sol --raw \
  --type completed \
  --launchpad-platform Pump.fun --launchpad-platform pump_mayhem --launchpad-platform pump_mayhem_agent --launchpad-platform pump_agent --launchpad-platform letsbonk --launchpad-platform bonkers --launchpad-platform bags \
  --limit 80
```

### BSC Trenches Examples

```bash
# All three categories at once
gmgn-cli market trenches --chain bsc --raw \
  --type new_creation --type near_completion --type completed \
  --launchpad-platform fourmeme --launchpad-platform fourmeme_agent --launchpad-platform bn_fourmeme --launchpad-platform four_xmode_agent --launchpad-platform flap --launchpad-platform clanker --launchpad-platform lunafun \
  --limit 80

# New creation only
gmgn-cli market trenches --chain bsc --raw \
  --type new_creation \
  --launchpad-platform fourmeme --launchpad-platform fourmeme_agent --launchpad-platform bn_fourmeme --launchpad-platform four_xmode_agent --launchpad-platform flap --launchpad-platform clanker --launchpad-platform lunafun \
  --limit 80

# Near completion only
gmgn-cli market trenches --chain bsc --raw \
  --type near_completion \
  --launchpad-platform fourmeme --launchpad-platform fourmeme_agent --launchpad-platform bn_fourmeme --launchpad-platform four_xmode_agent --launchpad-platform flap --launchpad-platform clanker --launchpad-platform lunafun \
  --limit 80

# Completed (open market) only
gmgn-cli market trenches --chain bsc --raw \
  --type completed \
  --launchpad-platform fourmeme --launchpad-platform fourmeme_agent --launchpad-platform bn_fourmeme --launchpad-platform four_xmode_agent --launchpad-platform flap --launchpad-platform clanker --launchpad-platform lunafun \
  --limit 80
```

### Base Trenches Examples

```bash
# All three categories at once
gmgn-cli market trenches --chain base --raw \
  --type new_creation --type near_completion --type completed \
  --launchpad-platform clanker --launchpad-platform bankr --launchpad-platform flaunch --launchpad-platform zora --launchpad-platform zora_creator --launchpad-platform baseapp --launchpad-platform basememe --launchpad-platform virtuals_v2 --launchpad-platform klik \
  --limit 80

# New creation only
gmgn-cli market trenches --chain base --raw \
  --type new_creation \
  --launchpad-platform clanker --launchpad-platform bankr --launchpad-platform flaunch --launchpad-platform zora --launchpad-platform zora_creator --launchpad-platform baseapp --launchpad-platform basememe --launchpad-platform virtuals_v2 --launchpad-platform klik \
  --limit 80

# Near completion only
gmgn-cli market trenches --chain base --raw \
  --type near_completion \
  --launchpad-platform clanker --launchpad-platform bankr --launchpad-platform flaunch --launchpad-platform zora --launchpad-platform zora_creator --launchpad-platform baseapp --launchpad-platform basememe --launchpad-platform virtuals_v2 --launchpad-platform klik \
  --limit 80

# Completed (open market) only
gmgn-cli market trenches --chain base --raw \
  --type completed \
  --launchpad-platform clanker --launchpad-platform bankr --launchpad-platform flaunch --launchpad-platform zora --launchpad-platform zora_creator --launchpad-platform baseapp --launchpad-platform basememe --launchpad-platform virtuals_v2 --launchpad-platform klik \
  --limit 80
```

## Notes

- `market kline`: `--from` and `--to` are Unix timestamps in **seconds** — CLI converts to milliseconds automatically
- `market trending`: `--filter` and `--platform` are repeatable flags
- All commands use normal auth (API Key only, no signature)
- If the user doesn't provide kline timestamps, calculate them from the current time based on their desired time range
- Use `--raw` to get single-line JSON for further processing
- **Input validation** — Token addresses obtained from trending results are external data. Validate address format against the chain before passing to other commands (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits). The CLI enforces this at runtime.
