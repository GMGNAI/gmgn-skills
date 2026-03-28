# Wallet Analysis — Full Workflow

When a user provides a wallet address and wants to know the wallet's investment style, track record, and whether it's worth following.

## Step 1 — Current Holdings

```bash
gmgn-cli portfolio holdings --chain <chain> --wallet <address> \
  --order-by usd_value --direction desc --limit 50
```

Check: what tokens they hold, position sizes, `usd_value`, `unrealized_profit` distribution, `profit_change` per position. A wallet holding many positions with strong unrealized gains is still in accumulation mode.

## Step 2 — Trading Stats

```bash
gmgn-cli portfolio stats --chain <chain> --wallet <address> --period 30d
```

Key metrics:
- `winrate` — ratio of profitable trades (0–1); > 0.6 is strong
- `realized_profit` — total USD profit locked in over 30 days
- `pnl` — profit/loss ratio = `realized_profit / total_cost`; `2.0` = doubled money
- `buy_count` / `sell_count` — trading frequency and style

## Step 3 — Recent Activity

```bash
gmgn-cli portfolio activity --chain <chain> --wallet <address> --limit 50
```

Look for:
- Trading frequency (multiple trades per day = active trader)
- Average holding duration: compare `last_active_timestamp` of buy vs sell events for the same token
- Token diversity: does the wallet trade many different tokens or focus on a few?
- Position sizing patterns: are buys consistent size or highly variable?

## Step 4 — If Wallet Is Followed on GMGN

If the user has followed this wallet on the GMGN platform:

> **Requires `GMGN_PRIVATE_KEY`** in `.env` — `track follow-wallet` uses signature auth. If the key is not configured, skip this step and note it in the conclusion.

```bash
gmgn-cli track follow-wallet --chain <chain> --wallet <address>
```

Shows real-time trade feed for this wallet. Check `is_open_or_close` (1 = full position open/close, 0 = partial) and `price_change` (how well past trades aged).

## Step 5 — Deep Dive: Evaluate Their Top Holdings

For the top 3–5 holdings by `usd_value`, run the full token research workflow to verify the quality of what this wallet holds.

→ See [`docs/workflow-token-research.md`](workflow-token-research.md) for the full 5-step token analysis.

## Conclusion Framework

After completing all steps, output a wallet profile:

```
Wallet Analysis: {short_address}
Chain: {chain} | Period: 30d
─── Performance ────────────────────────────
Win Rate:       {winrate × 100}%
Realized P&L:   ${realized_profit}
PnL Ratio:      {pnl}x
Trades:         {buy_count} buys / {sell_count} sells
─── Style ──────────────────────────────────
Trading Style:  Day trader / Swing trader / Holder
                (Day trader: many trades/day; Swing: holds days–weeks; Holder: few sells)
Token Focus:    Meme / DeFi / Mixed / Specific sector
─── Current Positions ──────────────────────
Top holdings by value: {token1}, {token2}, {token3}
Open unrealized P&L: ${total_unrealized}
─── Smart Money Score ──────────────────────
Are their picks confirmed by other smart money? (check smart_degen_count on top holdings)
─── Verdict ────────────────────────────────
🟢 Worth following — strong win rate + consistent P&L + smart money overlap
🟡 Watch first — promising stats but limited data or inconsistent style
🔴 Not recommended — low win rate, losses, or high-risk behavior patterns
```

## Related Workflows

- [`workflow-smart-money-profile.md`](workflow-smart-money-profile.md) — deeper behavior analysis: trading style, take-profit/stop-loss patterns, copy-trade ROI estimate, and leaderboard comparison
