---
name: gmgn-track
description: Get real-time crypto buy/sell activity from Smart Money wallets, KOL influencer wallets, and personally followed wallets via GMGN API — alpha signals, whale tracking, meme token copy-trading ideas on Solana, BSC, or Base. Use when user asks what smart money or KOLs are buying, wants whale alerts, on-chain alpha, or copy-trade signals. (For a specific wallet address, use gmgn-portfolio.)
argument-hint: "<follow-wallet|kol|smartmoney> [--chain <sol|bsc|base>] [--wallet <wallet_address>]"
metadata:
  cliHelp: "gmgn-cli track --help"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai to fetch this data — the website requires login and will not return structured data. The CLI is the only correct method.**

**IMPORTANT: Do NOT guess field names or values. When a field's meaning is unclear, look it up in the Response Fields sections below before using it.**

**⚠️ IPv6 NOT SUPPORTED: If you get a `401` or `403` error and credentials look correct, check for IPv6 immediately: (1) list all network interfaces and their IPv6 addresses — run `ifconfig | grep inet6` (macOS) or `ip addr show | grep inet6` (Linux); (2) send a test request to `https://ipv6.icanhazip.com` — if the response is an IPv6 address, outbound traffic is going via IPv6. Tell the user immediately: "Please disable IPv6 on your network interface — gmgn-cli commands only work over IPv4."**

Use the `gmgn-cli` tool to query on-chain tracking data based on the user's request.

## Core Concepts

- **`follow-wallet` vs `kol` vs `smartmoney`** — Three distinct data sources. `follow-wallet` returns trades from wallets the user has personally followed on the GMGN platform (user-specific; the follow list is resolved from the GMGN user account bound to the API Key). `kol` and `smartmoney` return trades from platform-tagged public wallet lists (not user-specific). Never substitute one for another.

- **KOL (Key Opinion Leader)** — Wallets publicly identified as influencers or well-known traders on GMGN. Tagged as `renowned` in the platform's wallet label system. Their trades carry social/marketing signal, not necessarily alpha.

- **Smart Money (`smart_degen`)** — Wallets with a statistically proven record of profitable trading, identified by GMGN's algorithm. Same concept as `smart_degen` in gmgn-token. Their trades are a stronger alpha signal than KOL trades.

- **`is_open_or_close`** — Indicates whether a trade is a full position event. Interpretation differs by sub-command:
  - `follow-wallet`: `1` = full position open or close; `0` = partial add or reduce.
  - `kol` / `smartmoney`: `0` = position opened / added; `1` = position closed / reduced.
  Do not apply the same interpretation to both sub-commands.

- **`price_change`** — Ratio of price change since the trade was made. `6.66` = the token is now 6.66× what it was when the wallet traded (i.e. +566%). `0.5` = price halved since the trade (-50%). Use this to assess "how well did this trade age."

- **`base_address` vs `quote_address`** — In a trading pair, `base_address` is the token being bought/sold; `quote_address` is what it was priced in (typically SOL native address on Solana). To get the token of interest, always read `base_address`.

- **`maker_info.tags`** — Array of platform labels on the wallet (e.g. `["kol", "gmgn"]`, `["smart_degen", "photon"]`). A wallet can carry multiple tags. Use `tag_rank` (follow-wallet only) to see the wallet's rank within each tag category.

- **Cluster signal** — When multiple followed/tracked wallets trade the same token in the same direction within a short time window, this is a stronger conviction signal than a single wallet. Highlight this pattern when it appears in results.

**When to use which sub-command:**
- `track follow-wallet` — user asks "what did the wallets I follow trade?", "show me my follow list trades", "show my followed wallet activity" → requires wallets followed via GMGN platform
- `track kol` — user asks "what are KOLs buying?", "show me influencer trades", "what are KOLs doing recently" → returns trades from known KOL wallets
- `track smartmoney` — user asks "what is smart money doing?", "show me whale trades", "what is smart money buying recently" → returns trades from smart money / whale wallets

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

- `gmgn-cli` installed globally — if missing, run: `npm install -g gmgn-cli`
- `GMGN_API_KEY` configured in `~/.config/gmgn/.env` — required for all sub-commands; no private key needed

## Rate Limit Handling

All tracking routes used by this skill go through GMGN's leaky-bucket limiter with `rate=10` and `capacity=10`. Sustained throughput is roughly `10 ÷ weight` requests/second, and the max burst is roughly `floor(10 ÷ weight)` when the bucket is full.

| Command | Route | Weight |
|---------|-------|--------|
| `track follow-wallet` | `GET /v1/trade/follow_wallet` | 3 |
| `track kol` | `GET /v1/user/kol` | 1 |
| `track smartmoney` | `GET /v1/user/smartmoney` | 1 |

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

The response is an object with a `list` array. Each item in `list` contains:

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

## Smart Money Behavior Interpretation

After receiving trade data, interpret the signals using these frameworks before presenting results. Do not just list trades — analyze what they mean.

### 1. Signal Strength Levels

| Level | Criteria |
|-------|----------|
| Weak | 1 KOL buys |
| Medium | 2–3 smart money buys in the same direction, OR 1 smart money full position open |
| Strong | ≥ 3 smart money wallets same direction within 30 min (cluster signal) |
| Very Strong | Cluster signal + full position opens + KOL joining the same trade |

### 2. Reading `is_open_or_close` — Conviction Signals

The field has opposite meanings by sub-command:

- **`follow-wallet`**: `1` = full position open or close; `0` = partial add or reduce.
- **`kol` / `smartmoney`**: `0` = position opened / added; `1` = position closed / reduced.

Full position events (full open or full close) carry much stronger conviction than partial adds. A wallet opening a full new position signals high confidence. A wallet doing a full close signals they are exiting completely — treat this as a potential exit signal for that token.

### 3. Using `price_change` to Evaluate Track Record

`price_change` is a ratio of current price vs price at trade time:
- `price_change > 2` → this wallet's trade aged well (token is now 2x+ since they bought) — strong conviction signal
- `price_change 1–2` → modest gain, trade is in profit
- `price_change < 1` → trade is underwater (current price below entry)

Use this to build a mental model of a wallet's past performance before acting on their current trades.

### 4. Cluster Signal Detection

When multiple trades hit the same `base_address` in a short time window, this is a convergence signal — stronger than any single trade. To identify:
- Group results by `base_address`
- Count distinct `maker` addresses trading the same direction
- If ≥ 3 distinct wallets buy the same token within ~30 min → highlight as **cluster signal**

Cluster signals from `smartmoney` are stronger than from `kol` alone.

### 5. Red Flags in Smart Money Data

- **Smart money selling** (`side = sell` + `is_open_or_close` = full close) → exit signal — evaluate whether to exit or reduce position
- **Only KOL buying, zero smart_degen** → social hype without fundamental backing; higher risk
- **Renowned buying + smart money selling simultaneously** → divergence signal — insiders may be distributing into retail/KOL demand; high risk
- **Single very large buy, no follow-through** → may be one-off; wait for confirmation from other wallets

## Output Format

### `track follow-wallet` / `track kol` / `track smartmoney` — Trade Feed

Present as a reverse-chronological trade feed. Do not dump raw JSON.

```
{timestamp}  {side}  {base_token.symbol}  ${amount_usd}  by {maker_info.name or short address}
             [{tags}]  Price: ${price_usd}  |  Price now: ${price_now}  ({price_change}x since trade)
```

Group by token if multiple trades hit the same token. Highlight tokens where several followed wallets traded in the same direction within a short window (cluster signal).

For `follow-wallet`, also show `is_open_or_close`: flag full position opens/closes distinctly from partial adds/reduces.

### Cluster Signal Summary

After presenting the trade feed, check for convergence signals. If ≥ 2 distinct wallets traded the same token in the same direction, display a summary block:

```
⚡ Convergence Signals
──────────────────────────────────────────
TOKEN_X ({short_address})
  5 smart money wallets — all BUY — $42,300 total — within 15 min
  Signal strength: STRONG

TOKEN_Y ({short_address})
  2 KOL wallets — BUY (full open) — $8,100 total
  Signal strength: MEDIUM
```

For STRONG signals: proceed to full token research before acting — see [`docs/workflow-token-research.md`](../../docs/workflow-token-research.md)
For MEDIUM signals: monitor and wait for more wallets to confirm before acting.

If no convergence signals are detected: output "No cluster signals detected in this result set."

To research any token surfaced by smart money activity, follow [`docs/workflow-token-research.md`](../../docs/workflow-token-research.md)

**Smart money leaderboard / wallet profiling:** When the user asks "which smart money wallets are best to follow", "rank wallets by win rate", or wants to compare wallet performance — use `track smartmoney` to collect active wallet addresses, then batch-query their stats via `gmgn-portfolio stats`. Full workflow: [`docs/workflow-smart-money-profile.md`](../../docs/workflow-smart-money-profile.md)

**Daily brief:** When the user asks for a market overview ("what's the market like today", "what is smart money buying today", "give me a daily brief") — combine `track smartmoney` + `track kol` with `gmgn-market trending`. Full workflow: [`docs/workflow-daily-brief.md`](../../docs/workflow-daily-brief.md)

## Safety Constraints

- **`follow-wallet` reveals your following list** — results expose which wallets you have followed on GMGN. Do not share raw output in public channels.
- **`track kol` / `track smartmoney` expose no personal data** — these use API Key auth only and return platform-tagged public wallet activity. Safe to share raw output.

## Notes

- All sub-commands use normal auth (API Key only, no signature required)
- `track follow-wallet` returns trades from wallets followed on the GMGN platform; the follow list is resolved automatically from the GMGN user account bound to the API Key — `--wallet` is optional
- Use `--raw` to get single-line JSON for further processing
- `track kol` / `track smartmoney` `--side` is a **client-side filter** — the CLI fetches all results then filters locally; it is NOT sent to the API
