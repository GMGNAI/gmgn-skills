# Early Project Screening — Workflow

Use this workflow to rapidly screen newly launched tokens from launchpads and identify whether any are worth a closer look, before committing to a full token research deep dive.

Use this workflow when:
- "early project screening" / "are any new tokens worth accumulating?"
- "screen the latest launched tokens for me"
- "which new tokens have smart money entering early?"
- "any new tokens on pump.fun worth watching?"
- User wants to filter new launchpad tokens for quality signals before buying

---

## Step 1 — Fetch Newly Launched Tokens

```bash
# Tokens just created, still on bonding curve
gmgn-cli market trenches --chain <chain> --type new_creation

# Tokens near bonding curve completion (about to graduate to DEX)
gmgn-cli market trenches --chain <chain> --type near_completion

# Tokens that have already graduated to open market
gmgn-cli market trenches --chain <chain> --type completed
```

**Which type to use:**
- `new_creation` — highest upside potential, highest risk. Many will fail.
- `near_completion` — approaching graduation, momentum building. Tighter window.
- `completed` — already trading on DEX, more liquidity but earlier gains may be gone.

From the results, note each token's `address`, `symbol`, `smart_degen_count`, `renowned_count`, `volume`, `swaps`, and `rug_ratio`.

**Tip — use filter flags to pre-screen at fetch time:**

```bash
# Fetch with safe baseline filter (server-side)
gmgn-cli market trenches --chain <chain> \
  --type new_creation --type near_completion \
  --filter-preset safe --sort-by smart_degen_count

# Strict: safe + require smart money + min 24h volume $1k
gmgn-cli market trenches --chain <chain> \
  --type new_creation --type near_completion \
  --filter-preset strict --sort-by smart_degen_count

# Custom: manual range filters (all sent server-side)
gmgn-cli market trenches --chain <chain> \
  --type new_creation \
  --max-rug-ratio 0.3 --max-bundler-rate 0.3 --max-insider-ratio 0.3 \
  --min-smart-degen-count 1 --min-volume-24h 1000
```

Using `--filter-preset safe` (or `strict`) tells the server to pre-filter results before returning — equivalent to Steps 2's "Discard immediately" criteria, applied before the response is sent.

---

## Step 2 — First-Pass Filter (In-Response Scan)

> **If you used `--filter-preset safe` or `--filter-preset strict` in Step 1, the rug_ratio, bundler_rate, and insider_ratio checks below are already applied server-side.** Verify the remaining signals manually.

Before running any CLI commands per token, apply a quick in-response filter on the trenches results:

**Discard immediately if:**
- `rug_ratio` > 0.3
- `is_wash_trading` = `true`
- `bundler_rate` > 0.3
- `rat_trader_amount_rate` > 0.3
- Zero `smart_degen_count` AND zero `renowned_count` AND volume < $10k

**Keep for deeper screening if any of:**
- `smart_degen_count` ≥ 1 (smart money has entered)
- `renowned_count` ≥ 1 (KOL has entered)
- `bluechip_owner_percentage` > 0 (quality wallet base)
- `volume` is strong relative to token age

Select up to **5 tokens** that pass this filter.

---

## Step 3 — Security Check (Per Token)

For each shortlisted token:

```bash
gmgn-cli token security --chain <chain> --address <token_address>
```

Hard stops — discard token immediately if:

| Field | Hard Stop |
|-------|-----------|
| `is_honeypot` | `"yes"` (BSC/Base) |
| `renounced_mint` (SOL) | `false` |
| `renounced_freeze_account` (SOL) | `false` |
| `rug_ratio` | `> 0.3` |
| `sell_tax` | `> 0.10` |
| `top_10_holder_rate` | `> 0.6` |

Proceed with tokens that pass all hard stops.

---

## Step 4 — Smart Money Early Entry Check

```bash
# Who's already in? (smart money holders)
gmgn-cli token holders --chain <chain> --address <token_address> \
  --tag smart_degen --order-by buy_volume_cur --direction desc --limit 10

# Top traders — any known wallets?
gmgn-cli token traders --chain <chain> --address <token_address> \
  --order-by profit --direction desc --limit 10
```

Strong signal:
- Smart money wallets entered **early** (check `buy_30m` / `buy_1h` counts on the holder — or cross-reference `last_active_timestamp` being recent)
- Multiple distinct smart money wallets (not one large wallet — that's concentration risk)
- Top traders show profit (token has already rewarded early holders, positive momentum)

Weak signal:
- Only one smart money wallet in
- Smart money wallet entered but `profit` is negative (they're underwater)

---

## Step 5 — Token Info Spot Check

```bash
gmgn-cli token info --chain <chain> --address <token_address>
```

Check:
- Social presence: `link.twitter_username`, `link.telegram`, `link.website` — at least one should exist
- `holder_count` — growing is a positive sign
- `wallet_tags_stat.smart_wallets` — confirms smart money count
- `cto_flag` — if `1`, community has taken over, dev is gone (neutral to positive, evaluate context)
- `creator_token_status` — `creator_close` means dev has sold (mixed: reduces dump risk, but also less team commitment for very new tokens)

---

## Screening Output

Present results as a table, then a per-token verdict:

```
Early Project Screening — {chain} / {type}
Screened: {N} tokens from trenches → {M} passed filter

# | Symbol | Address (short) | Smart Degens | Rug Risk | Security | Verdict
1 | ...     | ...             | {N} wallets  | {X}      | ✅/⚠️/🚫  | Watch / Small position / Skip
...

─── Top Pick ───────────────────────────────
{SYMBOL}: Smart money in early, security clean, social present
→ Suggested action: Small exploratory position / Watch for 1h / Skip
```

**Verdict scale:**
- 🟢 **Small position** — clean security + smart money early entry + social presence
- 🟡 **Watch** — some positive signals but missing key indicators; monitor for 30–60 min
- 🔴 **Skip** — any hard stop triggered, or no smart money interest at all

---

## Follow-Up Actions

For any token rated 🟢:
- Run full due diligence: [`workflow-token-research.md`](workflow-token-research.md)
- Check risk warnings before sizing up: [`workflow-risk-warning.md`](workflow-risk-warning.md)
- Execute swap if satisfied: use `gmgn-swap` skill

---

## Related Workflows

- [`workflow-token-research.md`](workflow-token-research.md) — full 5-step token analysis
- [`workflow-risk-warning.md`](workflow-risk-warning.md) — ongoing risk monitoring for held positions
- [`workflow-market-opportunities.md`](workflow-market-opportunities.md) — trending token discovery (graduated tokens with volume)
