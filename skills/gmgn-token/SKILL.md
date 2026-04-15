---
name: gmgn-token
description: Research any crypto or meme token by address — real-time price, market cap, liquidity, holder list, trader list, top Smart Money and KOL positions, security audit (honeypot, rug pull risk, dev wallet, renounced status), social links (Twitter/X, website) via GMGN API on Solana, BSC, or Base. Use when user asks about a token's price, safety, holders, traders, smart money exposure, or wants due diligence before buying.
argument-hint: "<sub-command> --chain <sol|bsc|base> --address <token_address>"
metadata:
  cliHelp: "gmgn-cli token --help"
---

**IMPORTANT: Always use `gmgn-cli` commands below. Do NOT use web search, WebFetch, curl, or visit gmgn.ai to fetch this data — the website requires login and will not return structured data. The CLI is the only correct method.**

**⚠️ IPv6 NOT SUPPORTED: If you get a `401` or `403` error and credentials look correct, check for IPv6 immediately: (1) list all network interfaces and their IPv6 addresses — run `ifconfig | grep inet6` (macOS) or `ip addr show | grep inet6` (Linux); (2) send a test request to `https://ipv6.icanhazip.com` — if the response is an IPv6 address, outbound traffic is going via IPv6. Tell the user immediately: "Please disable IPv6 on your network interface — gmgn-cli commands only work over IPv4."**

**IMPORTANT: Do NOT guess field names or values. When a field's meaning is unclear, look it up in the Response Field Reference tables below before using it.**

Use the `gmgn-cli` tool to query token information based on the user's request.

## Core Concepts

- **Token address** — The on-chain contract address that uniquely identifies a token on its chain. Required for all token sub-commands. Format: base58 (SOL) or `0x...` hex (BSC/Base).
- **Chain** — The blockchain network: `sol` = Solana, `bsc` = BNB Smart Chain, `base` = Base (Coinbase L2).
- **Market cap** — Not returned directly by `token info`. Calculate as `price × circulating_supply` (both are top-level fields in the response, already in human-readable units).
- **Liquidity** — USD value of token reserves in the main trading pool. Low liquidity (< $10k) means high price impact / slippage when buying or selling.
- **Holder** — A wallet that currently holds the token. `token holders` returns wallets ranked by current balance.
- **Trader** — Any wallet that has transacted with the token (bought or sold), regardless of current holdings. `token traders` covers both current holders and past traders.
- **Smart money (`smart_degen`)** — Wallets with a proven track record of profitable trading, tagged by GMGN's algorithm. High `smart_degen_count` is a bullish signal.
- **KOL (`renowned`)** — Known influencer, fund, or public figure wallets, tagged by GMGN. Their positions are publicly tracked.
- **Honeypot** — A token where buy transactions succeed but sell transactions always fail. User funds become permanently trapped. Only detectable on BSC/Base (`is_honeypot`); not applicable on SOL.
- **Renounced (mint / freeze / ownership)** — The developer has permanently given up that authority. On SOL: `renounced_mint` (cannot create new supply) and `renounced_freeze_account` (cannot freeze wallets) both `true` is the safe baseline. On EVM: `owner_renounced` `"yes"` means no admin backdoors.
- **rug_ratio** — A 0–1 risk score estimating the likelihood of a rug pull. Values above `0.3` are high-risk. Do not treat as a binary safe/unsafe flag — use in combination with other signals.
- **Bonding curve** — Price discovery mechanism used by launchpads (e.g. Pump.fun, letsbonk). Token price rises as more is bought. When the curve fills, the token "graduates" to an open DEX pool. `is_on_curve: true` means the token has not graduated yet.
- **Wallet tags** — GMGN-assigned labels on wallets: `smart_degen` (smart money), `renowned` (KOL), `sniper` (launched at token open), `bundler` (bot-bundled buy), `rat_trader` (insider/sneak trading). Use `--tag` to filter `token holders` / `token traders` by these labels.

## Sub-commands

| Sub-command | Description |
|-------------|-------------|
| `token info` | Basic info + realtime price, liquidity, market cap, total supply, holder count, social links (market cap = price × circulating_supply) |
| `token security` | Security metrics (honeypot, taxes, holder concentration, contract risks) |
| `token pool` | Liquidity pool info (DEX, reserves, liquidity depth) |
| `token holders` | Top token holders list with profit/loss breakdown |
| `token traders` | Top token traders list with profit/loss breakdown |

## Supported Chains

`sol` / `bsc` / `base`

## Prerequisites

- `gmgn-cli` installed globally — if missing, run: `npm install -g gmgn-cli`
- `GMGN_API_KEY` configured in `~/.config/gmgn/.env`

## Rate Limit Handling

All token routes used by this skill go through GMGN's leaky-bucket limiter with `rate=10` and `capacity=10`. Sustained throughput is roughly `10 ÷ weight` requests/second, and the max burst is roughly `floor(10 ÷ weight)` when the bucket is full.

| Command | Route | Weight |
|---------|-------|--------|
| `token info` | `GET /v1/token/info` | 1 |
| `token security` | `GET /v1/token/security` | 1 |
| `token pool` | `GET /v1/token/pool_info` | 1 |
| `token holders` | `GET /v1/market/token_top_holders` | 5 |
| `token traders` | `GET /v1/market/token_top_traders` | 5 |

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
| `--tag` | No | — | Wallet filter: `renowned` (KOL wallets) / `smart_degen` (smart money). Omit to return all wallets. |
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

### `--tag` + `--order-by` Combination Guide

`--tag` and `--order-by` are independent — all `--order-by` values are valid with or without `--tag`. Omitting `--tag` returns all wallets (no filter).

Recommended combinations for common use cases:

| Goal | `--tag` | `--order-by` |
|------|---------|--------------|
| Largest smart money holders by supply | `smart_degen` | `amount_percentage` |
| Smart money with highest realized profit | `smart_degen` | `profit` |
| Smart money sitting on unrealized gains | `smart_degen` | `unrealized_profit` |
| Smart money aggressively accumulating | `smart_degen` | `buy_volume_cur` |
| Smart money distributing (exit signal) | `smart_degen` | `sell_volume_cur` |
| KOLs who already took profit | `renowned` | `profit` |
| KOLs still holding with paper gains | `renowned` | `unrealized_profit` |
| Largest holders overall (no filter) | *(omit)* | `amount_percentage` |

## Response Field Reference

### `token info` — Key Fields

The response has five nested objects: `pool`, `dev`, `link`, `stat`, `wallet_tags_stat`. Access fields with dot notation when parsing (e.g. `link.website`, `stat.top_10_holder_rate`, `dev.creator_address`).

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
| `launchpad` | Launchpad identifier (e.g. `pump`, `moonshot`) |
| `launchpad_status` | Launchpad state: `0` = not opened, `1` = live, `2` = migrated |
| `launchpad_progress` | Launchpad bonding-curve progress (0–1) |
| `launchpad_platform` | Launchpad platform name |
| `migrated_pool` | Pool address after migration |
| `migration_market_cap` | Market cap at migration time (USD, float) |
| `migration_market_cap_quote` | Quote currency for `migration_market_cap` |
| `ath_price` | All-time-high price (USD, float) |
| `locked_ratio` | Ratio of supply locked (0–1, float) |

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

**`dev` Object** — Token creator / developer info

| Field | Description |
|-------|-------------|
| `dev.creator_address` | Creator wallet address |
| `dev.creator_token_balance` | Creator's current token balance |
| `dev.creator_token_status` | Creator holding status: `hold` (still holding) / `sell` (sold/exited) |
| `dev.top_10_holder_rate` | Ratio of supply held by top 10 wallets (0–1) |
| `dev.twitter_name_change_history` | Array of past Twitter username changes (each entry has `twitter_username`, `rename_timestamp`) |
| `dev.dexscr_ad` | Creator bought a DEXScreener ad: `1` = yes, `0` = no |
| `dev.dexscr_update_link` | Creator updated DEXScreener socials/links: `1` = yes, `0` = no |
| `dev.dexscr_boost_fee` | Creator used DEXScreener Boost: `1` = yes, `0` = no |
| `dev.dexscr_trending_bar` | Token appeared in DEXScreener trending bar: `1` = yes, `0` = no |
| `dev.dexscr_ad_ts` | Timestamp of DEXScreener ad purchase (Unix seconds) |
| `dev.dexscr_update_link_ts` | Timestamp of DEXScreener link update (Unix seconds) |
| `dev.dexscr_boost_ts` | Timestamp of DEXScreener Boost (Unix seconds) |
| `dev.dexscr_trending_bar_ts` | Timestamp of DEXScreener trending bar appearance (Unix seconds) |
| `dev.cto_flag` | Token has been Community Takeover'd (original dev abandoned): `1` = yes, `0` = no |
| `dev.fund_from` | Address that funded the creator wallet |
| `dev.fund_from_ts` | Timestamp of that funding event (Unix seconds) |
| `dev.creator_open_count` | Number of tokens this creator has previously launched |
| `dev.twitter_del_post_token_count` | Number of posts the creator deleted from Twitter |
| `dev.twitter_create_token_count` | Number of tokens the creator has promoted on Twitter |
| `dev.offchain` | Whether the token is an offchain token |
| `dev.ath_token_info` | Creator's all-time-high token info object (optional); see sub-fields below |
| `dev.ath_token_info.ath_token` | Contract address of the creator's best-performing token ever |
| `dev.ath_token_info.ath_mc` | All-time-high market cap of that token (USD, string) |
| `dev.ath_token_info.avatar` | Token logo URL |
| `dev.ath_token_info.symbol` | Token symbol |
| `dev.ath_token_info.name` | Token name |
| `dev.ath_token_info.creation_timestamp` | Token creation time (Unix seconds) |

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
| `stat.private_vault_hold_rate` | Ratio held by private vault (vanish) addresses — displayed as "vanish" in GMGN UI (0–1) |

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

### `token holders` / `token traders` — Response Fields

The response is an object with a `list` array. Each item in `list` represents one wallet.

**Identity & Holdings**

| Field | Description |
|-------|-------------|
| `address` | Wallet address |
| `account_address` | Token account address (the on-chain account holding the token, distinct from the wallet address) |
| `addr_type` | Address type: `0` = regular wallet, `2` = exchange / liquidity pool |
| `exchange` | Exchange or pool name if `addr_type` is `2` (e.g. `pump_amm`, `raydium`) |
| `wallet_tag_v2` | Rank label in this list (e.g. `TOP1`, `TOP2`, ...) |
| `native_balance` | Native token balance in smallest unit (lamports for SOL) |
| `balance` | Current token balance (human-readable units) |
| `amount_cur` | Same as `balance` — current token amount held |
| `usd_value` | USD value of current holdings at current price |
| `amount_percentage` | Ratio of total supply held (0–1); e.g. `0.05` = 5% |
| `is_on_curve` | `true` = still on bonding curve (pump.fun pre-graduation); `false` = open market |
| `is_new` | Whether this is a newly created wallet |
| `is_suspicious` | Whether this wallet is flagged as suspicious |
| `transfer_in` | Whether the current holding was received via transfer (not bought) |

**Trading Summary**

| Field | Description |
|-------|-------------|
| `buy_volume_cur` | Total buy volume in USD |
| `sell_volume_cur` | Total sell volume in USD |
| `buy_amount_cur` | Total tokens bought |
| `sell_amount_cur` | Total tokens sold |
| `sell_amount_percentage` | Ratio of bought tokens that have been sold (0–1); `1.0` = fully exited |
| `buy_tx_count_cur` | Number of buy transactions |
| `sell_tx_count_cur` | Number of sell transactions |
| `netflow_usd` | Net USD flow = sell income − buy cost (negative = net spent) |
| `netflow_amount` | Net token flow = bought − sold (positive = still holding net position) |

**Cost & P&L**

| Field | Description |
|-------|-------------|
| `avg_cost` | Average buy price in USD per token |
| `avg_sold` | Average sell price in USD per token |
| `history_bought_cost` | Total USD spent buying |
| `history_bought_fee` | Total fees paid on buys in USD |
| `history_sold_income` | Total USD received from selling |
| `history_sold_fee` | Total fees paid on sells in USD |
| `total_cost` | Total cost basis including fees |
| `profit` | Total profit in USD (realized + unrealized) |
| `profit_change` | Total profit ratio = profit / total_cost |
| `realized_profit` | Realized profit in USD from completed sells |
| `realized_pnl` | Realized profit ratio = realized_profit / buy_cost |
| `unrealized_profit` | Unrealized profit in USD on current holdings at current price |
| `unrealized_pnl` | Unrealized profit ratio; `null` if no current holdings |

**Transfer History**

| Field | Description |
|-------|-------------|
| `current_transfer_in_amount` | Tokens received via transfer (not bought) in current period |
| `current_transfer_out_amount` | Tokens sent out via transfer (not sold) in current period |
| `history_transfer_in_amount` | Historical total tokens received via transfer |
| `history_transfer_in_cost` | Estimated cost basis of transferred-in tokens |
| `history_transfer_out_amount` | Historical total tokens sent out via transfer |
| `history_transfer_out_income` | Estimated income from transferred-out tokens |
| `history_transfer_out_fee` | Fees paid on transfer-outs |
| `transfer_in_count` | Number of inbound transfers |
| `transfer_out_count` | Number of outbound transfers |

**Timing**

| Field | Description |
|-------|-------------|
| `start_holding_at` | Unix timestamp when wallet first acquired this token |
| `end_holding_at` | Unix timestamp when wallet fully exited; `null` if still holding |
| `last_active_timestamp` | Unix timestamp of most recent on-chain activity for this token |
| `last_block` | Block number of last activity |

**Wallet Identity**

| Field | Description |
|-------|-------------|
| `name` | Wallet display name (if known) |
| `twitter_username` | Twitter / X username |
| `twitter_name` | Twitter / X display name |
| `avatar` | Avatar image URL |
| `tags` | Platform-level wallet tags (e.g. `["kol"]`, `["smart_degen"]`, `["axiom"]`) |
| `maker_token_tags` | Token-specific behavior tags for this wallet (e.g. `["bundler"]`, `["paper_hands"]`, `["top_holder"]`) |
| `created_at` | Wallet creation timestamp (Unix seconds); `0` if unknown |

**Last Transaction Records**

Each of the following is an object with `name`, `address`, `timestamp`, `tx_hash`, `type`:

| Field | Description |
|-------|-------------|
| `native_transfer` | Most recent native token (SOL/BNB/ETH) transfer associated with this wallet |
| `token_transfer` | Most recent token transfer (buy or sell) |
| `token_transfer_in` | Most recent inbound token transfer |
| `token_transfer_out` | Most recent outbound token transfer |

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

### `token traders` — `--tag` + `--order-by` Combination Guide

Use this table to pick the right combination for common `token traders` use cases:

| Use case | `--tag` | `--order-by` |
|----------|---------|-------------|
| Smart money with highest buy volume | `smart_degen` | `buy_volume_cur` |
| Smart money with highest sell volume (exit signal) | `smart_degen` | `sell_volume_cur` |
| KOLs recently active | `renowned` | `last_active_timestamp` |
| Smart money most profitable traders | `smart_degen` | `profit` |
| Snipers still holding | `sniper` | `amount_percentage` |
| Smart money sitting on biggest unrealized gains | `smart_degen` | `unrealized_profit` |
| KOLs who already took profit | `renowned` | `profit` |

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

## Token Quick Scoring Card

After fetching `token security` and `token info`, apply this scoring card to give a structured verdict. Do not skip this step when the user asks for a safety check or due diligence.

| Field | ✅ Safe | ⚠️ Warning | 🚫 Danger (Hard Stop) |
|-------|---------|-----------|----------------------|
| `is_honeypot` | `"no"` | — | `"yes"` → **stop immediately** |
| `open_source` | `"yes"` | `"unknown"` | `"no"` |
| `owner_renounced` | `"yes"` | `"unknown"` | `"no"` |
| `renounced_mint` (SOL) | `true` | — | `false` |
| `renounced_freeze_account` (SOL) | `true` | — | `false` |
| `rug_ratio` | `< 0.10` | `0.10–0.30` | `> 0.30` |
| `top_10_holder_rate` | `< 0.20` | `0.20–0.50` | `> 0.50` |
| `creator_token_status` | `creator_close` | — | `creator_hold` |
| `buy_tax` / `sell_tax` | `0` | `0.01–0.05` | `> 0.10` |
| `sniper_count` | `< 5` | `5–20` | `> 20` |
| `smart_wallets` (from `wallet_tags_stat`) | `≥ 3` | `1–2` | `0` (bearish, not a hard stop) |
| `renowned_wallets` (from `wallet_tags_stat`) | `≥ 1` | — | `0` (neutral, not a hard stop) |

**Final scoring logic:**
- If `is_honeypot = "yes"` → **hard stop immediately**, do not proceed regardless of other signals
- If other 🚫 fields present → **skip** (strong warning — present to user)
- `smart_wallets = 0` alone is NOT a hard stop — it means no smart money interest yet, which is bearish but not disqualifying for very new tokens
- If 3+ ⚠️ with no 🚫 → **needs more research** — present findings and ask user how to proceed
- If mostly ✅ with `smart_wallets ≥ 3` → **worth researching** — proceed to holders/traders analysis

## Workflow: Full Token Due Diligence

When the user asks for a full token research / due diligence, follow the steps in [`docs/workflow-token-research.md`](../../docs/workflow-token-research.md).

Steps: `token info` → `token security` → `token pool` → market heat check → `token holders/traders` (smart money signals) → Decision Framework.

**For a more comprehensive report** (user asks for a "deep report", "full analysis", "is this worth a large position"), use the extended workflow: [`docs/workflow-project-deep-report.md`](../../docs/workflow-project-deep-report.md). This adds a scored multi-dimension analysis (fundamentals + security + liquidity + smart money conviction + price action) and produces a full written report.

**For active risk monitoring** on a held position (user asks "any risk warnings", "are whales dumping", "is liquidity still healthy"), follow: [`docs/workflow-risk-warning.md`](../../docs/workflow-risk-warning.md). Uses `token security` + `token pool` + `token holders` to flag whale exits, liquidity drain, and developer dumps.

---

## Output Format

### `token info` — Summary Card

Present as a concise card. Do not dump raw JSON.

```
{symbol} ({name})
Price: ${price}  |  Market Cap: ~${price × circulating_supply}  |  Liquidity: ${liquidity}
Holders: {holder_count}  |  Smart Money: {wallet_tags_stat.smart_wallets}  |  KOLs: {wallet_tags_stat.renowned_wallets}
Social: @{link.twitter_username}  |  {link.website}  |  {link.telegram}
```

If any social fields are empty, omit them rather than showing `null`.

### `token security` — Risk Assessment Summary

After fetching security data, present a structured risk summary using this format:

```
Token: {symbol}  |  Chain: {chain}  |  Address: {short address}
─── Security ──────────────────────────────────────
Contract verified:    ✅ yes  / 🚫 no / ⚠️ unknown
Owner renounced:      ✅ yes  / 🚫 no / ⚠️ unknown
Honeypot:             ✅ no   / 🚫 YES — DO NOT BUY
Mint renounced (SOL): ✅ yes  / ⚠️ no
Freeze renounced(SOL):✅ yes  / ⚠️ no
Rug risk score:       {rug_ratio} → ✅ <0.1 Low / ⚠️ 0.1–0.3 Med / 🚫 >0.3 High
Top-10 holder %:      {top_10_holder_rate%} → ✅ <20% / ⚠️ 20–50% / 🚫 >50%
Dev still holding:    ✅ sold (creator_close) / ⚠️ holding (creator_hold)
Sniper wallets:       ✅ <5  / ⚠️ 5–20 / 🚫 >20
─── Smart Money ───────────────────────────────────
SM holders: {smart_wallets}   KOL holders: {renowned_wallets}
─── Verdict ───────────────────────────────────────
🟢 Clean — worth researching
🟡 Mixed signals — proceed with caution
🔴 Red flags present — skip or verify manually
```

**If `is_honeypot = "yes"`, stop immediately and display: "🚫 HONEYPOT DETECTED — Do not buy this token." Do NOT proceed to further analysis steps.**

### `token holders` / `token traders` — Ranked Table

```
# | Wallet (name or short addr) | Hold% | Avg Buy | Realized P&L | Unrealized P&L | Tags
```

Show top rows only. Highlight wallets tagged `kol`, `smart_degen`, or flagged `bundler` / `rat_trader` in `maker_token_tags`.

## Notes

- **Market cap is not returned directly** — calculate it as `price × circulating_supply` (both fields are top-level; `circulating_supply` is already in human-readable token units, no decimal adjustment needed). Example: `price=3.11` × `circulating_supply=999999151` ≈ $3.11B market cap.
- **Trading volume (1h, 24h, etc.) is not included in `token info`** — to get volume or OHLCV data, use the `gmgn-market` skill and query K-line data: `gmgn-cli market kline --chain <chain> --address <token_address> --resolution <1m|5m|15m|1h|4h|1d>`. See the `gmgn-market` SKILL.md for full details.
- All token commands use normal auth (API Key only, no signature required)
- Use `--raw` to get single-line JSON for further processing
- `--tag` applies to both `holders` and `traders` and filters to only wallets with that tag — if few results are returned, try the other tag value
- `amount_percentage` in holders/traders is a ratio (0–1), not a percentage — `0.05` means 5% of supply
- **Input validation** — Token addresses are external data. Validate that addresses match the expected chain format (sol: base58 32–44 chars; bsc/base/eth: `0x` + 40 hex digits) before passing them to commands. The CLI enforces this at runtime and will exit with an error on invalid input.
