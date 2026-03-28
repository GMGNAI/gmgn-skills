# Daily Market Brief — Workflow

Use this workflow to generate a structured morning/daily overview of market conditions, smart money activity, and risk signals — without needing a specific token or wallet in mind.

Use this workflow when:
- "what's the market like today?"
- "what is smart money buying today?"
- "daily brief" / "give me a market overview"
- "any opportunities worth watching?"
- "any risks I should be aware of today?"
- User wants a broad market situational awareness update

---

## Step 1 — Market Pulse (Trending Tokens)

Fetch trending tokens across multiple time windows to gauge market momentum:

```bash
# Short-term heat (last 1h)
gmgn-cli market trending --chain <chain> --interval 1h \
  --order-by volume --limit 20

# Medium-term momentum (last 6h)
gmgn-cli market trending --chain <chain> --interval 6h \
  --order-by volume --limit 20
```

From the results, assess:
- **Market phase:** Are top tokens mostly meme/speculation (risk-on) or utility/DeFi (risk-off)?
- **Breadth:** Are many tokens trending or just 1–2? Broad trends = healthier market.
- **Smart money confirmation:** Do trending tokens have non-zero `smart_degen_count`? Trending without smart money = retail-driven pump.
- **Volume quality:** Compare `volume` vs `swaps`. High volume with low swap count = whale activity. High swaps with low volume = retail noise.

Key signal summary from this step:
```
Market Phase:    Risk-on (meme dominated) / Risk-off (utility) / Mixed
Breadth:         Broad ({N} tokens trending) / Narrow (1–2 tokens dominate)
Smart Money:     Confirmed in trending / Absent (retail-driven)
```

---

## Step 2 — Smart Money Activity (What Are They Buying/Selling?)

```bash
# What smart money traded in the last few hours
gmgn-cli track smartmoney --chain <chain>

# What KOLs are doing
gmgn-cli track kol --chain <chain>
```

From the results:
- Group trades by direction: **net buying** vs **net selling** per token
- Identify tokens where **multiple** smart money wallets traded the same direction (cluster signal)
- Note `price_change` on each trade — positive = their past entries aged well (good track record lately)
- Flag any token appearing in both smart money AND trending data — double confirmation

Output for this step:
```
Smart Money Moves (last ~2h):
  Buying:  TOKEN_A ({N} wallets), TOKEN_B ({N} wallets)
  Selling: TOKEN_C ({N} wallets)
  Notable: TOKEN_A appears in both trending AND smart money buys → strong signal
```

---

## Step 3 — New Token Watch (Early Opportunities)

```bash
# Tokens near graduation — imminent DEX listing
gmgn-cli market trenches --chain <chain> --type near_completion

# Recently graduated tokens — fresh DEX liquidity
gmgn-cli market trenches --chain <chain> --type completed
```

Quick filter: from results, surface tokens with:
- `smart_degen_count` ≥ 1
- `rug_ratio` < 0.2
- Non-zero `volume` and `swaps`

List up to 3 tokens that pass this quick filter as "early watch" candidates.

---

## Step 4 — Risk Scan (Anything to Avoid Today?)

For any tokens the user currently holds (if known), or for the top tokens from steps 1–2:

```bash
gmgn-cli token security --chain <chain> --address <token_address>
```

Flag immediately if any held/watched token shows:
- `rug_ratio` increase (compare to prior knowledge)
- `top_10_holder_rate` > 0.5
- `creator_token_status` = `creator_hold` (dev still in)
- `is_wash_trading` = `true`

If no specific tokens to check, skip this step and note it in the brief.

---

## Daily Brief Output

```
═══════════════════════════════════════════
  DAILY MARKET BRIEF — {chain} — {date}
═══════════════════════════════════════════

📊 MARKET PULSE
  Phase:        Risk-on / Risk-off / Mixed
  Breadth:      {N} tokens trending (broad/narrow)
  Top movers:   TOKEN_A (+X%), TOKEN_B (+X%), TOKEN_C (+X%)
  Smart money:  Present in trending ✅ / Absent (retail-driven) ⚠️

🧠 SMART MONEY MOVES
  Buying:
    • TOKEN_A — {N} wallets accumulating, avg price_change +{X}%
    • TOKEN_B — {N} wallets, fresh entry
  Selling:
    • TOKEN_C — {N} wallets reducing positions
  Cluster signal: TOKEN_A (trending + smart money overlap) 🔥

🌱 EARLY WATCH
  • TOKEN_X — near graduation, {N} smart degens in, rug_ratio {X}
  • TOKEN_Y — just graduated, strong volume, clean security
  (Run /gmgn-token → workflow-early-project-screening for deeper check)

⚠️ RISK SIGNALS
  • No active warnings detected
  OR
  • TOKEN_Z: whale concentration rising (top_10 = {X}%), monitor closely

─── SUGGESTED ACTIONS ─────────────────────
  Opportunity:  TOKEN_A worth researching → run full token research
  Caution:      TOKEN_C seeing smart money exits → tighten stop
  New entry:    TOKEN_X early screening recommended
═══════════════════════════════════════════
```

---

## Follow-Up Actions

From the brief, typical next steps:
- **Deep dive on an opportunity** → [`workflow-token-research.md`](workflow-token-research.md)
- **Screen early tokens further** → [`workflow-early-project-screening.md`](workflow-early-project-screening.md)
- **Check a specific wallet that showed up** → [`workflow-smart-money-profile.md`](workflow-smart-money-profile.md)
- **Risk check on a held position** → [`workflow-risk-warning.md`](workflow-risk-warning.md)
- **Execute a trade** → use `gmgn-swap` skill

---

## Related Workflows

- [`workflow-market-opportunities.md`](workflow-market-opportunities.md) — focused opportunity discovery from trending
- [`workflow-early-project-screening.md`](workflow-early-project-screening.md) — detailed new token screening
- [`workflow-risk-warning.md`](workflow-risk-warning.md) — active risk monitoring
