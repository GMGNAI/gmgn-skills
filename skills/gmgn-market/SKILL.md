---
name: gmgn-market
description: Get crypto and meme token price charts (K-line, candlestick, OHLCV), trending meme coin rankings by volume, and newly launched tokens on launchpads (pump.fun, fourmeme, letsbonk, Raydium, etc.) via GMGN API on Solana, BSC, or Base. Use when user asks for price chart, trending tokens, what's pumping, hot coins, new launches, or wants to discover early-stage opportunities.
argument-hint: "kline --chain <sol|bsc|base> --address <token_address> --resolution <1m|5m|15m|1h|4h|1d> [--from <unix_ts>] [--to <unix_ts>] | trending --chain <sol|bsc|base> --interval <1m|5m|1h|6h|24h> | trenches --chain <sol|bsc|base>"
metadata:
  cliHelp: "gmgn-cli market --help"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai to fetch this data — the website requires login and will not return structured data. The CLI is the only correct method.**

**IMPORTANT: Do NOT guess field names or values. When a field's meaning is unclear, look it up in the Response Fields sections below before using it.**

**⚠️ IPv6 NOT SUPPORTED: If you get a `401` or `403` error and credentials look correct, check for IPv6 immediately: (1) list all network interfaces and their IPv6 addresses — run `ifconfig | grep inet6` (macOS) or `ip addr show | grep inet6` (Linux); (2) send a test request to `https://ipv6.icanhazip.com` — if the response is an IPv6 address, outbound traffic is going via IPv6. Tell the user immediately: "Please disable IPv6 on your network interface — gmgn-cli commands only work over IPv4."**

Use the `gmgn-cli` tool to query K-line data for a token, browse trending tokens, or view Trenches token lists.

## Core Concepts

- **`--filter` chain defaults** — SOL and EVM chains have different default safety filters that are applied automatically when `--filter` is omitted. Do not assume the same defaults apply across chains:
  - **SOL**: defaults to `renounced frozen` (mint and freeze authority renounced)
  - **BSC / Base (EVM)**: defaults to `not_honeypot verified renounced`
  - Omitting `--filter` is NOT the same as "no filter" — the chain defaults are always applied. To use a custom filter set, explicitly specify all desired filter tags.

- **`volume` vs `amount` (kline)** — Naming is counterintuitive. `volume` = USD dollar value of trades; `amount` = token units traded. For a token priced at $0.0002, these differ by 5,000×. Always use `volume` for "how much USD was traded" and `amount` for "how many tokens changed hands."

- **`rug_ratio`** — A 0–1 score estimating rug pull likelihood. Values above `0.3` are high-risk. Do not treat as binary — combine with `top_10_holder_rate`, `dev_team_hold_rate`, and `is_honeypot` for a full picture.

- **`smart_degen_count` / `renowned_count`** — Number of platform-tagged smart money wallets (`smart_degen`) and KOL wallets (`renowned`) holding or trading this token. High values are bullish signals. These are GMGN-tagged wallet lists, not user-defined.

- **`hot_level`** — Trending intensity score. Higher = more actively traded right now. Not normalized — compare relative values within the same result set, not across time windows.

- **`renounced_mint` / `renounced_freeze_account`** — SOL-specific. Indicate whether the creator gave up the ability to mint more tokens or freeze wallets. Both being `1` is a safety baseline on Solana. Always `false` on EVM chains (concept does not apply).

- **`is_honeypot`** — EVM-specific (BSC / Base). Indicates whether the token contract prevents selling. Always empty/null on SOL — do not interpret an empty value as "not a honeypot" on Solana.

- **`creator_token_status`** — Dev holding status. `creator_hold` = dev still holds tokens (sell pressure risk). `creator_close` = dev has sold or burned their allocation (exit signal confirmed).

- **`cto_flag`** — Community Takeover flag. `1` = original dev abandoned the project and a community group took over marketing/development. Neutral to positive signal; evaluate in context.

- **Trenches categories** — Three lifecycle stages of launchpad tokens: `new_creation` (just created, still on bonding curve), `near_completion` (bonding curve nearly full, about to graduate), `completed` (graduated to open market / DEX). In the response, `near_completion` is always returned under the key `data.pump` regardless of the input `--type`.

- **`wash_trading` / `rat_trader_amount_rate` / `bundler_rate`** — Risk signals for artificial activity. `is_wash_trading` = coordinated fake volume detected. `rat_trader_amount_rate` = ratio of insider/sneak trading. `bundler_rate` = ratio of bot-bundled buys at launch. High values (> 0.3) suggest manipulated price action.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `market kline` | Token candlestick / OHLCV data and trading volume over a time range |
| `market trending` | Trending tokens ranked by swap activity — use `--interval` to specify the time window (e.g. `1m` for 1-minute hottest, `1h` for 1-hour trending) |
| `market trenches` | Newly launched launchpad platform tokens — **use this when the user asks for "new tokens", "just launched tokens", "latest tokens on pump.fun/letsbonk"**. Three categories: `new_creation` (just created), `near_completion` (bonding curve almost full), `completed` (graduated to open market / DEX) |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `gmgn-cli` installed globally — if missing, run: `npm install -g gmgn-cli`
- `GMGN_API_KEY` configured in `~/.config/gmgn/.env`

## Rate Limit Handling

All market routes used by this skill go through GMGN's leaky-bucket limiter with `rate=10` and `capacity=10`. Sustained throughput is roughly `10 ÷ weight` requests/second, and the max burst is roughly `floor(10 ÷ weight)` when the bucket is full.

| Command | Route | Weight |
|---------|-------|--------|
| `market kline` | `GET /v1/market/token_kline` | 2 |
| `market trending` | `GET /v1/market/rank` | 1 |
| `market trenches` | `POST /v1/trenches` | 3 |

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
| "1m trending" / "hottest right now" | `1m` |
| "5m" / "5 minute" | `5m` |
| "1h" / "1 hour" / no time specified (default) | `1h` |
| "6h" / "6 hour" | `6h` |
| "24h" / "today" / "daily" | `24h` |

| Option | Description |
|--------|-------------|
| `--chain` | Required. `sol` / `bsc` / `base` |
| `--interval` | Required. `1m` / `5m` / `1h` / `6h` / `24h` (default `1h`) |
| `--limit <n>` | Number of results (default 100, max 100) |
| `--order-by <field>` | Sort field: `default` / `swaps` / `marketcap` / `history_highest_market_cap` / `liquidity` / `volume` / `holder_count` / `smart_degen_count` / `renowned_count` / `gas_fee` / `price` / `change1m` / `change5m` / `change1h` / `creation_timestamp` |
| `--direction <asc\|desc>` | Sort direction (default `desc`) |
| `--filter <tag...>` | Repeatable filter tags (chain-specific). **⚠️ SOL defaults: `renounced frozen`; BSC/Base defaults: `not_honeypot verified renounced`.** Omitting `--filter` is NOT "no filter" — chain defaults always apply. **sol** tags: `renounced` / `frozen` / `burn` / `token_burnt` / `has_social` / `not_social_dup` / `not_image_dup` / `dexscr_update_link` / `not_wash_trading` / `is_internal_market` / `is_out_market`. **evm** tags: `not_honeypot` / `verified` / `renounced` / `locked` / `token_burnt` / `has_social` / `not_social_dup` / `not_image_dup` / `dexscr_update_link` / `is_internal_market` / `is_out_market` |
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

Full workflow for discovering market opportunities: [`docs/workflow-market-opportunities.md`](../../docs/workflow-market-opportunities.md)

Steps: fetch trending (50 results, safe filters) → AI multi-factor analysis (smart money, volume, momentum, liquidity, maturity) → present top 5 table with rationale → offer deep dive or swap.

When results contain interesting tokens, proceed to full token due diligence: [`docs/workflow-token-research.md`](../../docs/workflow-token-research.md)

**For new / launchpad tokens** (`market trenches`): apply the structured early project screening workflow that includes security check and smart money entry detection — [`docs/workflow-early-project-screening.md`](../../docs/workflow-early-project-screening.md)

**For a daily market overview** (user asks "what's the market like today", "give me a daily brief", "what is smart money buying today"): combine `market trending` + `market trenches` with `gmgn-track smartmoney` — [`docs/workflow-daily-brief.md`](../../docs/workflow-daily-brief.md)

## Token Quality Filter Criteria

When evaluating tokens returned from `market trending` or `market trenches`, apply these criteria to quickly separate high-quality opportunities from noise. Do not present raw results without filtering.

### Pass / Watch / Skip Criteria

| Signal | 🟢 Pass | 🟡 Watch | 🔴 Skip |
|--------|---------|---------|---------|
| `smart_degen_count` | ≥ 3 | 1–2 | 0 |
| `rug_ratio` | < 0.1 | 0.1–0.3 | > 0.3 |
| `creator_token_status` | `creator_close` | — | `creator_hold` |
| `is_wash_trading` | `false` | — | `true` → skip immediately |
| `top_10_holder_rate` | < 0.20 | 0.20–0.50 | > 0.50 |
| `liquidity` | > $50k | $10k–$50k | < $10k |
| `has_social` (or any social field present) | yes | — | no (weak signal only) |

**Quick disqualification rule:** If `rug_ratio > 0.3` OR `is_wash_trading = true` OR `is_honeypot = 1` → skip immediately, no further analysis needed.

**Strong buy signal combination:** `smart_degen_count ≥ 3` + `rug_ratio < 0.2` + `creator_close` + `is_wash_trading = false` + `liquidity > $50k` → high-quality opportunity, proceed to full token research.

For full due diligence on any token surfaced here: [`docs/workflow-token-research.md`](../../docs/workflow-token-research.md)

## Token Lifecycle Stage

Use field combinations to determine what stage a token is in. This affects how signals should be interpreted.

### Stage 1 — Early (New Born)

**Indicators:**
- `creation_timestamp` < 1 hour ago
- `hot_level` low or just starting to rise
- `smart_degen_count = 0`, `renowned_count = 0`

**Interpretation:** Too early for smart money signals. No on-chain track record. High risk, high potential reward. **Wait for Stage 2 confirmation before acting.** Only the most risk-tolerant traders enter here.

### Stage 2 — Breakout

**Indicators:**
- `smart_degen_count ≥ 3` AND rising
- Volume surging (compare `swaps_1h` vs `swaps_24h / 24` — significantly higher)
- `price_change_percent1h > 20%`
- `creator_token_status = creator_hold` is OK at this stage (dev hasn't distributed yet)

**Interpretation:** Strongest entry signal. Smart money is accumulating. Verify security before acting. This window is often short — act on confirmation, not anticipation.

### Stage 3 — Distribution

**Indicators:**
- `creator_token_status = creator_close` (dev has sold their allocation)
- `renowned_count` buying (late social signal — KOLs often enter after smart money)
- `smart_degen_count` plateauing or declining
- Volume still high but momentum slowing

**Interpretation:** Late stage entry. Smart money may be exiting into retail/KOL demand. Higher risk for new entries. If already holding from Stage 2, evaluate exit levels.

### Stage 4 — Decline

**Indicators:**
- Volume declining across all windows
- `holder_count` declining
- `rat_trader_amount_rate` high (insider/sneak trading dominating)
- `smart_degen_count = 0` or clearly declining

**Interpretation:** Avoid new entries entirely. If still holding, consider exiting. The opportunity has likely passed.

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
| `--filter-preset` | No | Named server-side filter preset: `safe` / `smart-money` / `strict` |
| `--sort-by` | No | Client-side sort per category: `smart_degen_count` / `renowned_count` / `volume_24h` / `volume_1h` / `swaps_24h` / `swaps_1h` / `rug_ratio` / `holder_count` / `usd_market_cap` / `created_timestamp` |
| `--direction` | No | Sort direction: `asc` / `desc` (default: `desc`; `asc` for `rug_ratio`) |
| `--min-*` / `--max-*` | No | Server-side filter range flags — see Filter Fields Reference below |

### Filter Presets

Presets are applied server-side: the API filters tokens before returning results.

| Preset | Server-side filters applied |
|--------|----------------------------|
| `safe` | `max_rug_ratio=0.3` + `max_bundler_rate=0.3` + `max_insider_ratio=0.3` |
| `smart-money` | `min_smart_degen_count=1` |
| `strict` | `max_rug_ratio=0.3` + `max_bundler_rate=0.3` + `max_insider_ratio=0.3` + `min_smart_degen_count=1` + `min_volume_24h=1000` |

**Preset + explicit flag interaction:** Explicit filter flags always override preset values. For example, `--filter-preset safe --max-rug-ratio 0.1` applies the `safe` preset but overrides rug_ratio threshold to `0.1`.

**All filter flags are sent as part of the API request body (server-side)** — the server filters tokens before returning results. Use `--limit 80` (the default maximum) to maximise the pool.

Response fields: `data.new_creation`, `data.pump`, `data.completed` — each is an array of `RankItem` (same fields as `market trending` rank items). **Important: `data.pump` in the response corresponds to `--type near_completion` in the request. The API always returns this category under the key `pump`, not `near_completion`.**

### Server-Side Filter Fields

All filter flags are sent as part of the API request body — the server filters tokens before returning results. Flags follow the naming convention `--min-{field}` / `--max-{field}`.

| Flag pair | Type | Description |
|-----------|------|-------------|
| `--min-volume-24h` / `--max-volume-24h` | float | 24h trading volume (USD) |
| `--min-net-buy-24h` / `--max-net-buy-24h` | float | 24h net buy volume (USD) |
| `--min-swaps-24h` / `--max-swaps-24h` | int | 24h total swap count |
| `--min-buys-24h` / `--max-buys-24h` | int | 24h buy count |
| `--min-sells-24h` / `--max-sells-24h` | int | 24h sell count |
| `--min-visiting-count` / `--max-visiting-count` | int | Visitor count |
| `--min-progress` / `--max-progress` | float | Bonding curve progress (0–1) |
| `--min-marketcap` / `--max-marketcap` | float | Market cap (USD) |
| `--min-liquidity` / `--max-liquidity` | float | Liquidity (USD) |
| `--min-created` / `--max-created` | string | Token age (e.g. `1m` / `5m` / `1h` / `24h`) |
| `--min-holder-count` / `--max-holder-count` | int | Holder count |
| `--min-top-holder-rate` / `--max-top-holder-rate` | float | Top-10 holder concentration (0–1) |
| `--min-rug-ratio` / `--max-rug-ratio` | float | Rug pull risk score (0–1) |
| `--min-bundler-rate` / `--max-bundler-rate` | float | Bundle-bot trading ratio (0–1) |
| `--min-insider-ratio` / `--max-insider-ratio` | float | Insider trading ratio (0–1) |
| `--min-entrapment-ratio` / `--max-entrapment-ratio` | float | Entrapment/Phishing trading ratio (0–1) |
| `--min-private-vault-hold-rate` / `--max-private-vault-hold-rate` | float | Private vault holding ratio (0–1) |
| `--min-top70-sniper-hold-rate` / `--max-top70-sniper-hold-rate` | float | Top-70 sniper holding ratio (0–1) |
| `--min-bot-count` / `--max-bot-count` | int | Bot wallet count |
| `--min-bot-degen-rate` / `--max-bot-degen-rate` | float | Bot-degen wallet ratio (0–1) |
| `--min-fresh-wallet-rate` / `--max-fresh-wallet-rate` | float | Fresh wallet ratio (0–1) |
| `--min-total-fee` / `--max-total-fee` | float | Total fee |
| `--min-smart-degen-count` / `--max-smart-degen-count` | int | Smart-money holder count |
| `--min-renowned-count` / `--max-renowned-count` | int | KOL / renowned wallet count |
| `--min-creator-balance-rate` / `--max-creator-balance-rate` | float | Creator holding ratio (0–1) |
| `--min-creator-created-count` / `--max-creator-created-count` | int | Creator's total token creation count |
| `--min-creator-created-open-count` / `--max-creator-created-open-count` | int | Creator's graduated token count |
| `--min-creator-created-open-ratio` / `--max-creator-created-open-ratio` | float | Creator's graduation ratio (0–1) |
| `--min-x-follower` / `--max-x-follower` | int | Twitter / X follower count |
| `--min-twitter-rename-count` / `--max-twitter-rename-count` | int | Twitter rename count |
| `--min-tg-call-count` / `--max-tg-call-count` | int | Telegram call count |

### Trenches Filter Examples

```bash
# Apply the safe preset (server-side)
gmgn-cli market trenches --chain sol --type new_creation --filter-preset safe

# Require at least 1 smart money holder (server-side)
gmgn-cli market trenches --chain sol --type new_creation --min-smart-degen-count 1

# Safe preset + require smart money + sort by smart degen count (server-side filter, client-side sort)
gmgn-cli market trenches --chain sol --type new_creation \
  --filter-preset safe --min-smart-degen-count 1 --sort-by smart_degen_count

# Strict preset — safe + smart money + min $1k volume (server-side)
gmgn-cli market trenches --chain sol --type new_creation --type near_completion \
  --filter-preset strict --sort-by smart_degen_count

# Manual range filters (all sent server-side)
gmgn-cli market trenches --chain sol --type new_creation \
  --max-rug-ratio 0.3 --max-bundler-rate 0.3 --max-insider-ratio 0.3 \
  --min-smart-degen-count 1 --min-volume-24h 1000

# Filter by token age: only tokens created within the last 30 minutes
gmgn-cli market trenches --chain sol --type new_creation --max-created 30m

# Filter by market cap range
gmgn-cli market trenches --chain sol --type new_creation \
  --min-marketcap 10000 --max-marketcap 500000
```

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

**After fetching trenches results, apply the Token Quality Filter Criteria section before presenting tokens to the user.** Do not dump raw results — filter first, then surface the strongest candidates.

### Trenches Filter Examples

```bash
# Quick safe screen — exclude rugs, wash trading, and bundlers
gmgn-cli market trenches --chain sol --type new_creation \
  --filter-preset safe --raw

# Smart money screen — only tokens with smart money or KOL presence
gmgn-cli market trenches --chain sol \
  --type new_creation --type near_completion \
  --filter-preset smart-money \
  --sort-by smart_degen_count --raw

# Strict screen — safe + smart money + minimum volume, sorted by smart degens
gmgn-cli market trenches --chain sol --type completed \
  --filter-preset strict --sort-by smart_degen_count --raw

# Custom filter — no wash trading, rug_ratio <= 0.2, at least 1 smart degen
gmgn-cli market trenches --chain sol \
  --type new_creation --type near_completion \
  --exclude-wash-trading --max-rug-ratio 0.2 --min-smart-degen 1 \
  --sort-by smart_degen_count --raw

# BSC — safe screen on new tokens from fourmeme
gmgn-cli market trenches --chain bsc --type new_creation \
  --launchpad-platform fourmeme --launchpad-platform fourmeme_agent \
  --filter-preset safe --sort-by volume_1h --raw

# Sort by rug_ratio ascending (safest first), no other filters
gmgn-cli market trenches --chain sol --type completed \
  --sort-by rug_ratio --raw

# Find tokens with many holders and strong 1h swap activity
gmgn-cli market trenches --chain sol --type completed \
  --min-holders 100 --min-swaps 50 \
  --sort-by swaps_1h --raw
```

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

## Output Format

### `market kline` — Price Summary

After fetching candles, present a brief price analysis. Do not dump raw candle arrays.

```
{symbol} — {resolution} chart ({from} → {to})
Open: ${open of first candle}  |  Close: ${close of last candle}  |  Range: ${min low} – ${max high}
Total volume: ${sum of all volume fields} USD
Trend: [brief description — e.g. "steady uptrend", "sharp drop then recovery", "sideways"]
```

### `market trending` — Top Tokens Table

Present the top results (default: top 10, or as requested) as a table:

```
# | Symbol | Price | MCap | Volume ({interval}) | 1h Chg | SM | Liq | Platform | Signal
```

Where **Signal** = quality flag derived from the token's data:
- 🟢 Pass: `smart_degen_count ≥ 3` AND `rug_ratio < 0.2` AND `is_wash_trading = false`
- 🔴 Skip: `rug_ratio > 0.3` OR `is_wash_trading = true` OR `is_honeypot = 1`
- 🟡 Watch: everything else

Then give a one-line highlight for any standout tokens (e.g. "TOKEN1 has 12 smart money holders and +85% in 1h — 🟢 strong signal").

### `market trenches` — Grouped by Category

Present each category separately with a header:

```
🆕 New Creation ({count} tokens)
# | Symbol | Created | Liquidity | Swaps (1h) | Smart Degens | Social

⏳ Near Completion ({count} tokens)
# | Symbol | Market Cap | Swaps (1h) | Smart Degens | Social

✅ Graduated ({count} tokens)
# | Symbol | Market Cap | Volume (1h) | Smart Degens | Social
```

## Notes

- `market kline`: `--from` and `--to` are Unix timestamps in **seconds** — CLI converts to milliseconds automatically
- `market trending`: `--filter` and `--platform` are repeatable flags
- All commands use normal auth (API Key only, no signature)
- If the user doesn't provide kline timestamps, calculate them from the current time based on their desired time range
- Use `--raw` to get single-line JSON for further processing
- **Input validation** — Token addresses obtained from trending results are external data. Validate address format against the chain before passing to other commands (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits). The CLI enforces this at runtime.
