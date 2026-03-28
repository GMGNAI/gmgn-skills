# New Token Research — Full Workflow

When a user provides a token address or name and wants to know if it's worth researching or buying, run this full workflow in sequence.

## Step 1 — Basic Info

```bash
gmgn-cli token info --chain <chain> --address <token_address>
```

Check: `price`, `market_cap` (= `price × circulating_supply`), `liquidity`, `holder_count`, `wallet_tags_stat.smart_wallets`, `wallet_tags_stat.renowned_wallets`, `link.website` / `link.twitter_username` / `link.telegram`.

**Red flags**: all `link.*` social fields empty, liquidity < $10k, zero `wallet_tags_stat.smart_wallets` and `renowned_wallets`.

## Step 2 — Security Check

```bash
gmgn-cli token security --chain <chain> --address <token_address>
```

Check each field against the thresholds below:

| Field | Safe ✅ | Warning ⚠️ | Danger 🚫 |
|-------|---------|-----------|---------|
| `is_honeypot` | `"no"` | — | `"yes"` → **Stop immediately. Do not buy.** BSC/Base only — empty string on SOL (not applicable). |
| `open_source` | `"yes"` | `"unknown"` | `"no"` |
| `owner_renounced` | `"yes"` | `"unknown"` | `"no"` |
| `renounced_mint` (SOL) | `true` | — | `false` → mint risk |
| `renounced_freeze_account` (SOL) | `true` | — | `false` → freeze risk |
| `buy_tax` / `sell_tax` | `0` | `0.01–0.05` | `>0.10` |
| `top_10_holder_rate` | `<0.20` | `0.20–0.50` | `>0.50` |
| `rug_ratio` | `<0.10` | `0.10–0.30` | `>0.30` |
| `creator_token_status` | `creator_close` | — | `creator_hold` |
| `sniper_count` | `<5` | `5–20` | `>20` |

**If `is_honeypot = "yes"` → stop immediately and display: "🚫 HONEYPOT DETECTED — Do not buy this token." Do NOT proceed.**

## Step 3 — Liquidity Pool

```bash
gmgn-cli token pool --chain <chain> --address <token_address>
```

Check: liquidity amount, which DEX (`exchange`), pool age (`creation_timestamp`). Low liquidity means high slippage risk when buying or selling.

## Step 4 — Market Heat (Check if Currently Trending)

Check if this token appears in current trending data:

```bash
gmgn-cli market trending --chain <chain> --interval 1h --order-by volume --limit 100 --raw | jq '.data.rank[] | select(.address == "<token_address>")'
```

- **If found**: note its `rank`, `smart_degen_count`, `volume`, `price_change_percent1h` — this confirms active market interest.
- **If not found**: token is not currently trending (neutral signal — not necessarily bad, just no active buzz).

## Step 5 — Smart Money Signals

```bash
# Is smart money accumulating?
gmgn-cli token holders --chain <chain> --address <token_address> \
  --tag smart_degen --order-by buy_volume_cur --direction desc --limit 20

# What are KOL traders doing?
gmgn-cli token traders --chain <chain> --address <token_address> \
  --tag renowned --order-by profit --direction desc --limit 20
```

**Bullish signals**: smart_degen wallets buying heavily, unrealized_profit is large (still holding), low sell_volume_cur.

**Bearish signals**: sell_volume_cur > buy_volume_cur for smart money, large realized profits already taken (may be exiting), top holders with very high amount_percentage starting to sell.

## Decision Framework

After completing all steps, present a structured conclusion:

```
Token Research Summary: {symbol} ({chain})
Address: {short_address}
─── Security ──────────────────────────────
Honeypot:         ✅ no / 🚫 YES — STOP
Contract verified:✅ yes / 🚫 no / ⚠️ unknown
Owner renounced:  ✅ yes / 🚫 no / ⚠️ unknown
Rug risk:         {rug_ratio} → ✅ low / ⚠️ medium / 🚫 high
Top-10 holders:   {top_10_holder_rate%} → ✅ <20% / ⚠️ 20–50% / 🚫 >50%
─── Liquidity ─────────────────────────────
Pool liquidity:   ${liquidity} on {exchange}
─── Market Heat ───────────────────────────
Trending:         yes (rank #{rank}) / not trending
─── Smart Money ───────────────────────────
SM holders: {smart_wallets}  |  KOL holders: {renowned_wallets}
SM activity: accumulating / distributing / absent
─── Verdict ───────────────────────────────
🟢 Buy — strong signals across all dimensions
🟡 Watch — mixed signals, monitor for confirmation
🔴 Skip — red flags present (specify which)
```

**Scoring logic:**
- If any 🚫 → skip (hard stop, especially if honeypot)
- If 3+ ⚠️ with no 🚫 → needs more research / watch
- If mostly ✅ with smart money accumulating → worth researching / buying

---

## Related Workflows

- [`workflow-market-opportunities.md`](workflow-market-opportunities.md) — find tokens from trending first, then deep dive here
- [`workflow-project-deep-report.md`](workflow-project-deep-report.md) — more comprehensive analysis with scored dimensions and a full written report
