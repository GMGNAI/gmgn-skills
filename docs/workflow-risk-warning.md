# Risk Warning — Structured Checklist Workflow

Use this workflow to assess whether a token currently held or being considered shows active risk signals: whale exit, liquidity drain, or developer dump.

Use this workflow when:
- "are any whales dumping this token?"
- "is the liquidity still healthy?"
- "are there any signs the developer is exiting?"
- "risk warning" / "is this project still safe to hold?"
- User wants to check if a held position is turning dangerous

---

## Step 1 — Token Security Snapshot

```bash
gmgn-cli token security --chain <chain> --address <token_address>
```

Immediate red flags (any one triggers danger):

| Field | Danger Signal |
|-------|--------------|
| `is_honeypot` | `"yes"` → sells are blocked, exit impossible (BSC/Base only) |
| `rug_ratio` | `> 0.3` → high rug pull probability |
| `top_10_holder_rate` | `> 0.5` → extreme concentration, whale exit risk |
| `creator_token_status` | `creator_hold` → dev still holds, dump risk active |
| `renounced_mint` (SOL) | `false` → dev can inflate supply at any time |
| `renounced_freeze_account` (SOL) | `false` → dev can freeze wallets |
| `sell_tax` | `> 0.10` → exit penalty is severe |
| `bundler_rate` | `> 0.3` → heavily bot-bundled at launch, artificial price support |
| `rat_trader_amount_rate` | `> 0.3` → insider trading detected |
| `is_wash_trading` | `true` → volume is fake |

---

## Step 2 — Liquidity Check

```bash
gmgn-cli token pool --chain <chain> --address <token_address>
```

Check for liquidity drain:

- **Current liquidity (USD):** < $10k = extreme exit slippage risk
- **Liquidity vs earlier baseline:** if you have a prior reading, compare. A drop of > 30% in a short period is a warning signal.
- **Pool age (`creation_timestamp`):** very new pools (< 1h) combined with other risk signals = high risk.
- **DEX (`exchange`):** verify it's a known DEX (Raydium, Uniswap, PancakeSwap). Unknown or single-sided pools are suspicious.

---

## Step 3 — Whale Holder Analysis

```bash
# Top holders by supply percentage
gmgn-cli token holders --chain <chain> --address <token_address> \
  --order-by amount_percentage --direction desc --limit 20

# Smart money holders — are they still in?
gmgn-cli token holders --chain <chain> --address <token_address> \
  --tag smart_degen --order-by amount_percentage --direction desc --limit 20
```

Warning signals:

- **Concentration:** top 1–3 wallets hold > 20% combined → single exit can crash price
- **Smart money exodus:** zero or declining `smart_degen` holders = conviction leaving
- **Wallet tags:** wallets tagged `bundler` or `rat_trader` in top holders = insider concentration risk

---

## Step 4 — Recent Trade Flow (Smart Money Direction)

```bash
gmgn-cli track smartmoney --chain <chain>
```

Filter results for the token address in question. Check:

- Are smart money wallets **selling** this token recently? (`is_open_or_close` = 1 on sell side for kol/smartmoney)
- Is `price_change` on recent smart money buys negative? (their entry is underwater — they may exit)
- Cluster of sells from multiple tracked wallets = strong exit signal

---

## Step 5 — Price and Volume Anomaly (K-line)

```bash
gmgn-cli market kline --chain <chain> --address <token_address> \
  --resolution 1h
```

Look for:

- **Volume spike without price increase** — selling pressure absorbing buy volume
- **Price drop with volume spike** — active dump in progress
- **Volume collapse** — liquidity evaporating, exit windows closing
- **Consecutive red candles after ATH** — distribution phase

---

## Risk Summary Output

After running all steps, output a structured risk verdict:

```
Risk Assessment: {TOKEN_SYMBOL} ({short_address})
Chain: {chain} | Checked: {timestamp}

─── Security ───────────────────────────────
Honeypot:            ✅ No / 🚫 YES — exit blocked
Rug ratio:           ✅ {X} / ⚠️ {X} / 🚫 {X} (> 0.3 danger)
Mint renounced:      ✅ Yes / 🚫 No
Dev holding:         ✅ Sold / 🚫 Still holding — dump risk

─── Liquidity ──────────────────────────────
Current liquidity:   ${X}  [✅ healthy / ⚠️ low / 🚫 critical]
Pool age:            {X} hours/days

─── Whale Concentration ────────────────────
Top 10 hold rate:    {X}%  [✅ < 20% / ⚠️ 20–50% / 🚫 > 50%]
Smart money holders: {N} wallets still in

─── Smart Money Flow ───────────────────────
Recent smart money: Buying ✅ / Mixed ⚠️ / Selling 🚫

─── Price Action ───────────────────────────
1h volume trend:     Normal / Spike (selling pressure) / Collapsing
Recent candles:      Accumulation / Distribution / Neutral

─── Overall Verdict ────────────────────────
🟢 No active risk signals — position appears stable
🟡 Watch closely — 1–2 warning signals present, monitor daily
🔴 HIGH RISK — multiple danger signals, consider exiting
```

---

## Related Workflows

- [`workflow-token-research.md`](workflow-token-research.md) — full pre-buy due diligence
- [`workflow-project-deep-report.md`](workflow-project-deep-report.md) — comprehensive project analysis
