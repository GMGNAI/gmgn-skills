# Project Deep Report — Comprehensive Token Analysis Workflow

Use this workflow when the user wants a thorough, multi-dimensional project analysis — going beyond basic due diligence to cover smart money conviction, holder quality, market positioning, and a final investment verdict.

Use this workflow when:
- "give me a full analysis of this project"
- "deep report" / "is this project worth a large position?"
- "give me a complete investment research report"
- User wants more than a quick check — they want a structured report before making a significant position decision

> For a quick pre-buy check, use [`workflow-token-research.md`](workflow-token-research.md) instead. This workflow is more comprehensive and produces a full written report.

---

## Step 1 — Fundamentals

```bash
gmgn-cli token info --chain <chain> --address <token_address>
```

Extract and assess:

| Field | What to Note |
|-------|-------------|
| `price` | Current price |
| Market cap | `price × circulating_supply` — compute this manually |
| `liquidity` | USD in pool — < $50k is thin for a "serious" position |
| `holder_count` | Total wallets holding. Growing = organic adoption |
| `wallet_tags_stat.smart_wallets` | Smart money holders count |
| `wallet_tags_stat.renowned_wallets` | KOL holders count |
| `link.*` | Social presence: Twitter, Telegram, website |
| `cto_flag` | Community takeover? |
| `creator_token_status` | Dev still holding or has sold? |

**Fundamental score (0–3):**
- +1 if market cap reasonable for the chain/category
- +1 if strong social presence (2+ active channels)
- +1 if `smart_wallets` ≥ 3 AND `holder_count` growing

---

## Step 2 — Security Assessment

```bash
gmgn-cli token security --chain <chain> --address <token_address>
```

**Hard stops (any one = do not proceed):**
- `is_honeypot = "yes"` (BSC/Base)
- `rug_ratio > 0.5`
- `renounced_mint = false` AND `renounced_freeze_account = false` (SOL) — both unrenounced
- `sell_tax > 0.15`

**Security score (0–4):**
- +1 if contract open source / renounced
- +1 if `rug_ratio < 0.1`
- +1 if `top_10_holder_rate < 0.3`
- +1 if no snipers (`sniper_count < 5`) and no wash trading

---

## Step 3 — Liquidity and Pool Health

```bash
gmgn-cli token pool --chain <chain> --address <token_address>
```

Assess:
- **Liquidity depth:** > $100k = healthy; $10k–$100k = thin; < $10k = high exit slippage
- **Pool age:** older pool = more stable price history
- **DEX:** recognized exchange (Raydium, Uniswap v3, PancakeSwap) = better
- **Bonding curve status** (`is_on_curve`): if still on curve, token has not graduated — higher volatility window

**Liquidity score (0–2):**
- +1 if liquidity > $50k
- +1 if DEX is major and pool age > 24h

---

## Step 4 — Smart Money Conviction Analysis

This is the key differentiator from basic token research.

```bash
# Smart money holders — are they accumulating or distributing?
gmgn-cli token holders --chain <chain> --address <token_address> \
  --tag smart_degen --order-by buy_volume_cur --direction desc --limit 20

# KOL holders
gmgn-cli token traders --chain <chain> --address <token_address> \
  --tag renowned --order-by profit --direction desc --limit 10

# Top holders overall — check concentration
gmgn-cli token holders --chain <chain> --address <token_address> \
  --order-by amount_percentage --direction desc --limit 20
```

Assess smart money conviction:

| Signal | Bullish | Bearish |
|--------|---------|---------|
| Smart money count | ≥ 3 distinct wallets | 0 or 1 |
| Net direction | `buy_volume_cur` > `sell_volume_cur` | Selling exceeds buying |
| Unrealized profit | Large (still holding, not selling) | Small or negative |
| Realized profit | Moderate (some took profit, healthy) | Very large (majority already exited) |
| KOL involvement | ≥ 1 KOL with active position | None |
| Wallet diversity | Multiple different wallets | One whale dominating |

**Smart money score (0–4):**
- +1 if `smart_wallets` ≥ 3
- +1 if net buy direction (buy_volume_cur > sell_volume_cur across smart wallets)
- +1 if average `unrealized_profit` is positive (they're still in profit, still holding)
- +1 if at least 1 KOL has an active position

---

## Step 5 — Price Action Context

```bash
# Recent price action — 4h candles, last 3 days
gmgn-cli market kline --chain <chain> --address <token_address> \
  --resolution 4h

# Is it currently trending?
gmgn-cli market trending --chain <chain> --interval 1h \
  --order-by volume --limit 100 --raw | jq '.data.rank[] | select(.address == "<token_address>")'
```

Look for:
- **Entry context:** Is price near a local bottom (potential value) or after a run-up (chasing)?
- **Volume confirmation:** Do bullish candles have higher volume than bearish candles?
- **Trending:** If it appears in trending with `smart_degen_count > 0`, momentum + conviction overlap

**Price action score (0–2):**
- +1 if price is not parabolic (< 5x from recent low) — not chasing
- +1 if volume is rising on up-candles (healthy accumulation pattern)

---

## Step 6 — Risk Factors Summary

Aggregate all warning signals from Steps 1–5:

| Category | Risk Level | Key Signals |
|----------|-----------|-------------|
| Security | ✅/⚠️/🚫 | honeypot, rug_ratio, concentration |
| Liquidity | ✅/⚠️/🚫 | pool size, pool age |
| Smart Money | ✅/⚠️/🚫 | count, direction, conviction |
| Holder Quality | ✅/⚠️/🚫 | bundler_rate, rat_trader_rate, wash_trading |
| Price Action | ✅/⚠️/🚫 | entry timing, momentum |

---

## Deep Report Output

```
╔══════════════════════════════════════════════════════╗
║        PROJECT DEEP REPORT — {SYMBOL}                ║
║        {chain} | {short_address} | {date}            ║
╚══════════════════════════════════════════════════════╝

📋 FUNDAMENTALS
  Price:          ${price}
  Market Cap:     ~${market_cap}
  Liquidity:      ${liquidity} on {exchange}
  Holders:        {holder_count}
  Social:         Twitter ✅/❌ | Telegram ✅/❌ | Website ✅/❌
  Dev Status:     {creator_close = sold ✅ / creator_hold = still in ⚠️}
  Fundamental Score: {X}/3

🔒 SECURITY
  Honeypot:       ✅ No / 🚫 YES
  Contract:       {open_source} | {renounced}
  Rug Risk:       {rug_ratio} → ✅/⚠️/🚫
  Concentration:  Top-10 hold {top_10_holder_rate%} → ✅/⚠️/🚫
  Wash Trading:   ✅ None / ⚠️ Detected
  Security Score: {X}/4

💧 LIQUIDITY
  Pool:           ${liquidity} | {exchange} | Age: {pool_age}
  Bonding Curve:  Graduated ✅ / Still on curve ⚠️
  Liquidity Score: {X}/2

🧠 SMART MONEY CONVICTION
  SM Holders:     {N} wallets
  Net Direction:  Accumulating ✅ / Distributing ⚠️ / Mixed
  SM Unrealized:  +{X}% avg (still holding) ✅ / Underwater ⚠️
  KOL Presence:   {N} KOL wallets active
  Smart Money Score: {X}/4

📈 PRICE ACTION
  Recent trend:   Healthy accumulation / Parabolic (avoid chasing) / Declining
  Trending now:   Yes (rank #{rank}) ✅ / Not trending
  Price Action Score: {X}/2

─── RISK FLAGS ──────────────────────────────────────
  {List any ⚠️ or 🚫 signals here, or "No major risk flags"}

─── TOTAL SCORE ─────────────────────────────────────
  {X} / 15

─── VERDICT ─────────────────────────────────────────
  🟢 STRONG BUY CANDIDATE (score ≥ 11, no hard stops)
     Smart money confirmed, clean security, healthy liquidity
     → Suggested: research position sizing, use gmgn-swap

  🟡 WATCHLIST (score 7–10, no hard stops)
     Some positive signals but missing key conviction indicators
     → Suggested: monitor for 24–48h, re-assess if SM increases

  🔴 SKIP (any hard stop OR score < 7)
     Risk factors outweigh opportunity
     → Reason: {specific flag}
╚══════════════════════════════════════════════════════╝
```

---

## Related Workflows

- [`workflow-token-research.md`](workflow-token-research.md) — faster pre-buy check (use when time-sensitive)
- [`workflow-risk-warning.md`](workflow-risk-warning.md) — ongoing monitoring after entering a position
- [`workflow-smart-money-profile.md`](workflow-smart-money-profile.md) — deep dive on specific smart money wallets holding this token
- [`workflow-market-opportunities.md`](workflow-market-opportunities.md) — find tokens to run this report on
