# Smart Money Profile — Behavior Analysis Workflow

When a user wants to understand a wallet's trading behavior in depth: what style they trade, when they take profit, when they cut losses, and whether copying them would be profitable.

Use this workflow when:
- "is this wallet a long-term holder or a short-term trader?"
- "what is this wallet's win rate, when does it take profit or cut losses?"
- "if I copied this wallet, what would my return be?"
- "smart money leaderboard, which wallets are most worth following?"
- User provides a wallet address and asks about trading style or copy-trade potential

> For basic "is this wallet worth following" analysis, see [`workflow-wallet-analysis.md`](workflow-wallet-analysis.md). This workflow goes deeper into behavior patterns and copy-trade estimation.

---

## Step 1 — Trading Stats (Both Periods)

Run stats for both 7d and 30d to detect performance trends:

```bash
gmgn-cli portfolio stats --chain <chain> --wallet <address> --period 7d
gmgn-cli portfolio stats --chain <chain> --wallet <address> --period 30d
```

Key metrics:

| Field | Meaning | Threshold |
|-------|---------|-----------|
| `winrate` | % of profitable trades (0–1) | > 0.6 strong, > 0.5 acceptable |
| `pnl` | realized_profit / total_cost multiplier | > 1.0 = net positive |
| `realized_profit` | USD profit locked in | context-dependent |
| `buy_count` / `sell_count` | trading frequency | high = active trader |
| `token_num` | number of distinct tokens traded | high = diversified |

**Trend signal:** If 7d `winrate` is significantly higher than 30d, performance is improving. If lower, recent form is declining.

---

## Step 2 — Activity Analysis (Style Inference)

```bash
gmgn-cli portfolio activity --chain <chain> --wallet <address> --limit 100
```

For each token that appears in both a buy and a sell event, compute holding duration:
- `sell.timestamp - buy.timestamp` in hours

**Style classification:**

| Holding Duration | Style Label |
|-----------------|-------------|
| < 1 hour | Scalper |
| 1h – 24h | Day trader |
| 1d – 7d | Swing trader |
| > 7d | Position / long-term holder |

Also check:
- **Position sizing consistency** — are buy amounts roughly similar (disciplined) or highly variable?
- **Token concentration** — does the wallet repeatedly trade the same tokens (specialist) or always new ones (trend chaser)?
- **Sell behavior** — do sells follow a pattern (e.g., always sells after 2–3x, or cuts at -30%)?

---

## Step 3 — Take-Profit and Stop-Loss Pattern

From `portfolio activity`, cross-reference buy price vs sell price for completed round trips:

- For each token: find a `buy` event followed by a `sell` event
- Compute approximate return: `(sell_total_usd - buy_total_usd) / buy_total_usd`
- Group outcomes: wins vs losses

Look for:
- **Typical gain at exit** — does the wallet consistently take profit at ~2x, ~5x, or higher?
- **Typical loss at cut** — does the wallet cut quickly at -20% or hold through large drawdowns?
- **Asymmetry** — wins larger than losses = positive expected value. Reverse = risk.

---

## Step 4 — Copy-Trade ROI Estimation (Approximate)

> **Note:** This is an approximation based on historical activity data, not a precise backtest.

For the wallet's last 20–30 completed trades (round-trip buys + sells):

1. List all buy events: token, amount_usd, timestamp
2. List all sell events for the same tokens
3. Compute per-trade return: `(sell_usd - buy_usd) / buy_usd`
4. Average the returns

**If you want to estimate "if I had followed today":**
For still-open positions (buy with no matching sell), use `portfolio holdings` to get current `usd_value` vs `cost`, computing unrealized return.

Present as:
```
Copy-trade estimate (last 30d completed trades):
  Avg return per trade: +X%
  Win rate:             X / Y trades profitable
  Best trade:           +X% on TOKEN
  Worst trade:          -X% on TOKEN
  Approximate 30d return if equal-weight copy: ~X%
⚠️ This is an approximation. Actual results depend on entry timing, slippage, and fees.
```

---

## Step 5 — Smart Money Leaderboard (Multi-Wallet Comparison)

When the user wants to compare multiple smart money wallets:

```bash
# Batch stats — compare up to 10 wallets at once
gmgn-cli portfolio stats --chain <chain> \
  --wallet <addr1> --wallet <addr2> --wallet <addr3> \
  --period 30d
```

Rank wallets by composite score. Suggested weights:
- `winrate` × 40%
- `pnl` × 40%
- `token_num` (diversity) × 10%
- Recency (7d winrate vs 30d winrate improvement) × 10%

To discover active smart money wallets to compare, first run:
```bash
gmgn-cli track smartmoney --chain <chain>
```
Extract unique wallet addresses from the results, then batch-query their stats.

---

## Output Template

```
Smart Money Profile: {short_address}
Chain: {chain} | Data: 7d + 30d

─── Performance ────────────────────────────
Win Rate (7d / 30d):  {X}% / {X}%     [trend: ↑ improving / ↓ declining / → stable]
PnL Ratio (30d):      {X}x
Realized Profit (30d): ${X}

─── Trading Style ──────────────────────────
Style:          Scalper / Day trader / Swing trader / Long-term holder
Avg Hold Time:  ~{X} hours / days
Position Size:  Consistent (disciplined) / Variable (opportunistic)
Token Focus:    Specialist (repeats tokens) / Trend chaser (always new)

─── Exit Behavior ──────────────────────────
Typical take-profit: ~+{X}% gain
Typical stop-loss:   ~-{X}% loss
Win/loss ratio:      {avg_win}x / {avg_loss}x

─── Copy-Trade Estimate ────────────────────
Approx. 30d return if copied: ~{X}%
Based on {N} completed trades
⚠️ Approximation only

─── Verdict ────────────────────────────────
🟢 High-conviction follow — strong stats, consistent style, favorable exit pattern
🟡 Selective follow — good stats but inconsistent or high-risk behavior
🔴 Avoid copying — low win rate, poor exit discipline, or declining form
```

---

## Related Workflows

- [`workflow-wallet-analysis.md`](workflow-wallet-analysis.md) — general wallet quality assessment
- [`workflow-token-research.md`](workflow-token-research.md) — deep dive on tokens this wallet holds
